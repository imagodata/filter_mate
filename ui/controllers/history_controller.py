# -*- coding: utf-8 -*-
"""The history of the project in one list, over the dock, and what Undo and Redo of the action bar would do.

Undo walks one of three histories, depending on what is open (``FilterMateApp.update_undo_redo_buttons``): the turns
of the agent while AGENT is open, the raster / point cloud filters of the current source, the vector filters of the
dock in the scope of the current layer. Nothing showed which, nor what they held. Here:

- a right-click on Undo or Redo (enabled or not), or "History…" in the menu of Compare, opens a panel that lists
  everything the three histories hold, newest first (``core/domain/history_timeline.py``): what Undo and Redo would
  take now is marked, an item undone is dimmed, the steps of the last turn of the agent are under it. The map before
  the selected item can be compared or pinned (``CompareController``);
- the tooltips of Undo and Redo say what they would undo or redo, from which history, and how far they can go
  (``history_tips.button_tip``).

No "back to this step": that would undo across three histories at once, each with rules of its own.
"""
from __future__ import annotations

import logging
import time
from typing import List, Optional

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QCoreApplication, QEvent, QObject, QPoint, QPointF, QRect, QSize, Qt, QTimer
from qgis.PyQt.QtGui import QBrush, QColor, QFont, QGuiApplication, QIcon, QPainter, QPixmap, QPolygonF
from qgis.PyQt.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel, QPushButton,
                                 QTreeWidget, QTreeWidgetItem, QVBoxLayout)

from ...core.domain.compare_states import pin_before
from ...core.domain.history_timeline import (KIND_AGENT, KIND_COVERAGE, KIND_STEP, KIND_VECTOR, TimelineItem,
                                             UndoFocus, counts, cross_items, label_of, map_before, mark, timeline,
                                             vector_items, walkable)
from ..styles.mockup_design import plugin_is_dark, tokens
from .history_tips import button_tip, history_name

logger = logging.getLogger("FilterMate.history")

UNDO_BUTTON, REDO_BUTTON = "pushButton_action_undo_filter", "pushButton_action_redo_filter"
PANEL_NAME = "frame_fm_history"
COLUMNS = 6  # origin, time, what, layers, features kept, mark
COLUMN_ORIGIN, COLUMN_TIME, COLUMN_WHAT, COLUMN_LAYERS, COLUMN_KEPT, COLUMN_MARK = range(COLUMNS)
INDEX_ROLE = Qt.ItemDataRole.UserRole
PANEL_WIDTH, PANEL_HEIGHT = 520, 420  # at most; a smaller screen or dock gives less
LABEL_LENGTH = 40  # the label of the step, above the map compared


def _tr(text: str) -> str:
    return QCoreApplication.translate("FilterMateDockWidget", text)


def _clock(seconds: float) -> str:
    return time.strftime("%H:%M", time.localtime(seconds)) if seconds > 0 else ""


def _short(label: str) -> str:
    text = " ".join((label or "").split())
    return text if len(text) <= LABEL_LENGTH else text[:LABEL_LENGTH - 1].rstrip() + "…"


def origin_icon(kind: str, colour: QColor, size: int = 16) -> QIcon:
    """Where an item comes from, drawn: a funnel for a filter of the dock, a grid for a raster / point cloud filter,
    a speech bubble for a turn of the agent, a dot for one of its steps."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(colour)
    unit = size / 16.0
    if kind == KIND_VECTOR:
        painter.drawPolygon(QPolygonF([QPointF(x * unit, y * unit) for x, y in
                                       ((2, 3), (14, 3), (9.5, 8.5), (9.5, 14), (6.5, 12.5), (6.5, 8.5))]))
    elif kind == KIND_COVERAGE:
        for x in (2.5, 8.5):
            for y in (2.5, 8.5):
                painter.drawRect(QRect(round(x * unit), round(y * unit), round(5 * unit), round(5 * unit)))
    elif kind == KIND_AGENT:
        painter.drawRoundedRect(QRect(round(2 * unit), round(2.5 * unit), round(12 * unit), round(8.5 * unit)),
                                2.5 * unit, 2.5 * unit)
        painter.drawPolygon(QPolygonF([QPointF(4.5 * unit, 10 * unit), QPointF(4.5 * unit, 14 * unit),
                                       QPointF(8.5 * unit, 10 * unit)]))
    else:
        painter.drawEllipse(QPointF(8 * unit, 8 * unit), 2.5 * unit, 2.5 * unit)
    painter.end()
    return QIcon(pixmap)


class HistoryPanel(QFrame):
    """The history of the project, newest first, in a window over the dock that closes when the user clicks out."""

    def __init__(self, parent) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName(PANEL_NAME)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.items: List[TimelineItem] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)
        head = QHBoxLayout()
        self.title = QLabel(_tr("History of the project"), self)
        self.title.setObjectName("label_fm_history_title")
        self.counts = QLabel(self)
        self.counts.setObjectName("label_fm_history_counts")
        head.addWidget(self.title)
        head.addStretch(1)
        head.addWidget(self.counts)
        layout.addLayout(head)
        self.tree = QTreeWidget(self)
        self.tree.setObjectName("treeWidget_fm_history")
        self.tree.setColumnCount(COLUMNS)
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.tree.setIconSize(QSize(16, 16))
        header = self.tree.header()
        header.setStretchLastSection(False)
        for column in range(COLUMNS):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COLUMN_WHAT, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COLUMN_LAYERS, QHeaderView.ResizeMode.Interactive)
        layout.addWidget(self.tree, 1)
        self.empty = QLabel(_tr("Nothing done in this project yet."), self)
        self.empty.setObjectName("label_fm_history_note")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty, 1)
        self.note = QLabel(_tr("Undone: the map no longer holds it."), self)
        self.note.setObjectName("label_fm_history_note")
        layout.addWidget(self.note)
        buttons = QHBoxLayout()
        self.compare_button = QPushButton(_tr("Compare with the map before this step"), self)
        self.pin_button = QPushButton(_tr("Pin the map before this step"), self)
        for button in (self.compare_button, self.pin_button):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.tree.itemSelectionChanged.connect(self._sync_buttons)

    def selected(self) -> Optional[TimelineItem]:
        rows = self.tree.selectedItems()
        index = rows[0].data(COLUMN_ORIGIN, INDEX_ROLE) if rows else None
        return self.items[index] if isinstance(index, int) and 0 <= index < len(self.items) else None

    def _sync_buttons(self) -> None:
        """Compare and pin the map before an item the map still holds; nothing for an item undone."""
        item = self.selected()
        for button in (self.compare_button, self.pin_button):
            button.setEnabled(item is not None and item.applied)
        self.note.setVisible(item is not None and not item.applied)

    def set_timeline(self, items: List[TimelineItem], focus: UndoFocus, sources: dict) -> None:
        """List ``items`` (newest first, the steps of a turn after it), what Undo and Redo take marked.

        ``sources``: the name of the layer of each raster / point cloud history, by key.
        """
        kept = self.selected()
        dark = bool(plugin_is_dark(self.parentWidget() or self))
        palette = tokens(dark)
        self._style(palette)
        colours = {KIND_VECTOR: palette["fm_strip_vector_text"], KIND_COVERAGE: palette["fm_strip_raster_text"],
                   KIND_AGENT: palette["fm_accent"], KIND_STEP: palette["fm_accent"]}
        muted, accent = QColor(palette["fm_text_muted"]), QColor(palette["fm_accent"])
        icons = {kind: origin_icon(kind, QColor(colour)) for kind, colour in colours.items()}
        self.tree.clear()
        self.items = list(items)
        to_select, turn = None, None
        for index, item in enumerate(self.items):
            row = QTreeWidgetItem()
            row.setData(COLUMN_ORIGIN, INDEX_ROLE, index)
            row.setIcon(COLUMN_ORIGIN, icons.get(item.kind, icons[KIND_STEP]))
            row.setText(COLUMN_TIME, _clock(item.time) if item.kind != KIND_STEP else "")
            row.setText(COLUMN_WHAT, item.label or "—")
            row.setText(COLUMN_LAYERS, ", ".join(item.layers))
            row.setText(COLUMN_KEPT, _tr("{} features kept").format(item.count) if item.count else "")
            marked = mark(item, focus)
            if marked:
                row.setText(COLUMN_MARK, _tr("Undo") if marked == "undo" else _tr("Redo"))
                row.setForeground(COLUMN_MARK, QBrush(accent))
            font = QFont(self.tree.font())
            font.setItalic(not item.applied)
            font.setBold(bool(marked))
            tip = self._tip(item, marked, sources)
            for column in range(COLUMNS):
                row.setFont(column, font)
                row.setToolTip(column, tip)
                if not item.applied and column != COLUMN_MARK:
                    row.setForeground(column, QBrush(muted))
            if item.kind == KIND_STEP and turn is not None:
                turn.addChild(row)
            else:
                self.tree.addTopLevelItem(row)
                turn = row if item.kind == KIND_AGENT else None
            if kept is not None and item.ref is kept.ref and item.kind == kept.kind and item.position == kept.position:
                to_select = row
            elif to_select is None and kept is None and marked == "undo":
                to_select = row  # what Undo would undo: the step most likely compared
        self.tree.expandAll()
        self.tree.setVisible(bool(self.items))
        self.empty.setVisible(not self.items)
        if to_select is not None:
            self.tree.setCurrentItem(to_select)
            to_select.setSelected(True)
        to_undo, to_redo = counts(self.items)
        self.counts.setText(_tr("{} to undo · {} to redo").format(to_undo, to_redo))
        self._sync_buttons()

    @staticmethod
    def _tip(item: TimelineItem, marked: str, sources: dict) -> str:
        lines = [_tr("History: {}").format(history_name(KIND_AGENT if item.kind == KIND_STEP else item.kind,
                                                        sources.get(item.key, "") if item.kind == KIND_COVERAGE else "")),
                 " ".join(part for part in (_clock(item.time), item.label) if part)]
        if item.layers:
            lines.append(", ".join(item.layers))
        if item.count:
            lines.append(_tr("{} features kept").format(item.count))
        if marked:
            lines.append(_tr("Undo would undo this step now.") if marked == "undo" else
                         _tr("Redo would redo this step now."))
        elif not item.applied:
            lines.append(_tr("Undone: the map no longer holds it."))
        return "\n".join(lines)

    def _style(self, palette: dict) -> None:
        """The colours of the theme of the dock, light or dark."""
        self.setStyleSheet(
            f"QFrame#{PANEL_NAME} {{ background: {palette['fm_group']}; border: 1px solid {palette['fm_group_border']}; }}"
            f"QLabel#label_fm_history_title {{ font-weight: 600; color: {palette['fm_text']}; }}"
            f"QLabel#label_fm_history_counts, QLabel#label_fm_history_note {{ color: {palette['fm_text_muted']}; }}"
            f"QTreeWidget#treeWidget_fm_history {{ background: {palette['fm_list']}; color: {palette['fm_text']};"
            f" border: 1px solid {palette['fm_group_border']}; }}"
            f"QTreeWidget#treeWidget_fm_history::item:selected {{ background: {palette['fm_active']};"
            f" color: {palette['fm_text']}; }}")


class HistoryController(QObject):
    """The history panel, its ways in (right-click on Undo and Redo, the menu of Compare) and the tooltips of Undo
    and Redo."""

    def __init__(self, dockwidget, integration=None, compare=None) -> None:
        super().__init__(dockwidget)
        self._dock = dockwidget
        self._integration = integration
        self._compare = compare
        self.panel: Optional[HistoryPanel] = None  # made when first opened
        self._connections = []
        self._timer = QTimer(self)  # the buttons set first: their tooltips once their state is final
        self._timer.setSingleShot(True)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self.refresh)
        self.buttons = [button for button in (getattr(dockwidget, UNDO_BUTTON, None),
                                              getattr(dockwidget, REDO_BUTTON, None)) if button is not None]
        for button in self.buttons:
            # A disabled button swallows its right-click (QAbstractButton): the panel opens from here, enabled or not.
            button.installEventFilter(self)
        self.history_action = self._separator = None
        menu = getattr(compare, "menu", None)
        if menu is not None:
            self._separator = menu.addSeparator()
            self.history_action = menu.addAction(_tr("History…"))
            self.history_action.triggered.connect(self._open_from_compare)
        self._connect(getattr(dockwidget, "undoRedoStateRequested", None), self.schedule_refresh)
        self._connect(getattr(dockwidget, "currentLayerChanged", None), self.schedule_refresh)
        self._connect(QgsProject.instance().cleared, self.close_panel)

    def _connect(self, signal, slot) -> None:
        if signal is not None:
            signal.connect(slot)
            self._connections.append((signal, slot))

    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        try:
            if event.type() == QEvent.Type.ContextMenu and watched in self.buttons:
                self.open(watched)
                return True
        except RuntimeError:  # the dock is being deleted
            pass
        return False

    # --- the histories --------------------------------------------------------------

    def _app(self):
        # The app is ``filter_mate_app`` (the initializer of the plugin), ``app`` on the former path.
        return getattr(self._dock, "filter_mate_app", None) or getattr(self._dock, "app", None)

    def _coverage(self):
        return getattr(self._integration, "coverage_controller", None) if self._integration is not None else None

    @staticmethod
    def _name(layer_id: str) -> str:
        layer = QgsProject.instance().mapLayer(layer_id)
        try:
            return layer.name() if layer is not None else ""
        except RuntimeError:  # deleted meanwhile
            return ""

    def read(self) -> List[TimelineItem]:
        """Everything the three histories hold, newest first."""
        groups = []
        app = self._app()
        vector = getattr(app, "history_manager", None) if app is not None else None
        if vector is not None:
            groups.append(vector_items(vector.get_undo_stack(), vector.get_redo_stack(), self._name))
        from ...core.services.cross_filter_service import get_cross_filter_service
        history = get_cross_filter_service().history
        for key in history.sources():
            groups.append(cross_items(key, history.undo_stack(key), history.redo_stack(key), self._name))
        from ...adapters.agent.turn_checkpoint import HISTORY_KEY
        from ...adapters.public_api.operations import _api_service
        agent = _api_service().history
        groups.append(cross_items(HISTORY_KEY, agent.undo_stack(HISTORY_KEY), agent.redo_stack(HISTORY_KEY),
                                  self._name, agent=True))
        return timeline(*groups)

    def focus(self) -> UndoFocus:
        """What Undo and Redo take now, chosen as ``FilterMateApp.update_undo_redo_buttons`` chooses: the agent while
        AGENT is open, else nothing out of FILTERING, else the current raster / point cloud source, else the vector
        filters in the scope of the current layer (``_entry_in_scope``)."""
        dock = self._dock
        agent_focus = getattr(dock, "agent_has_focus", None)
        if callable(agent_focus) and agent_focus():
            return self._agent_focus()
        if getattr(dock, "tabTools_current_index", 0) != 0:
            return UndoFocus()
        coverage = self._coverage()
        layer = getattr(coverage, "active_layer", None) if coverage is not None else None
        if layer is not None:
            try:
                layer_id, name = layer.id(), layer.name()
            except RuntimeError:
                return UndoFocus(KIND_COVERAGE)
            history = coverage.service.history
            undo, redo = history.undo_stack(layer_id), history.redo_stack(layer_id)
            return UndoFocus(KIND_COVERAGE, undo[-1:], redo[-1:], len(undo), len(redo), name)
        return self._vector_focus(coverage)

    def _agent_focus(self) -> UndoFocus:
        from ...adapters.agent.turn_checkpoint import HISTORY_KEY
        from ...adapters.public_api.operations import _api_service
        chat = getattr(self._dock, "_agent_chat", None)
        state = chat.undo_state() if chat is not None else None
        if state is None:
            return UndoFocus(KIND_AGENT)
        history = _api_service().history
        undo = history.undo_stack(HISTORY_KEY) if state["can_undo"] else ()
        redo = history.redo_stack(HISTORY_KEY) if state["can_redo"] else ()  # nothing while the agent works
        return UndoFocus(KIND_AGENT, undo[-1:], redo[-1:], len(undo), len(redo))

    def _vector_focus(self, coverage) -> UndoFocus:
        from ...adapters.undo_redo_handler import _entry_in_scope
        dock = self._dock
        app = self._app()
        history = getattr(app, "history_manager", None) if app is not None else None
        current = getattr(dock, "current_layer", None)
        if history is None or current is None or getattr(app, "_undo_redo_handler", None) is None:
            return UndoFocus(KIND_VECTOR)
        try:
            current_id = current.id()
        except RuntimeError:
            return UndoFocus(KIND_VECTOR)
        if current_id not in (getattr(dock, "PROJECT_LAYERS", None) or {}):
            return UndoFocus(KIND_VECTOR)
        # Undo / Redo also restore the layers to filter checked on screen when their button is on.
        button = getattr(dock, "pushButton_checkable_filtering_layers_to_filter", None)
        targets = (dock.get_layers_to_filter() or []) if button is not None and button.isChecked() else []

        def takes(entry) -> bool:
            return _entry_in_scope(entry, current_id, targets)
        undo_stack, redo_stack = history.get_undo_stack(), history.get_redo_stack()
        undo_left, redo_left = walkable(undo_stack, takes), walkable(redo_stack, takes)
        undo = tuple(undo_stack[-1:]) if undo_left else ()
        redo = tuple(redo_stack[-1:]) if redo_left else ()
        # The raster / point cloud targets of a vector source follow its Undo and Redo when the run they recorded is
        # the next one (CoverageModeController.run_vector_source_task).
        if coverage is not None:
            try:
                cross = coverage.service.history
                runs = (getattr(coverage, "_linked_runs", None) or {}).get(current_id) or []
                done = (getattr(coverage, "_linked_redo", None) or {}).get(current_id) or []
                if undo and undo[0].layer_ids and undo[0].layer_ids[0] == current_id and runs:
                    operation = cross.peek_undo(current_id)
                    if coverage._run_is_next(runs[-1], operation):
                        undo += (operation,)
                if redo and redo[0].layer_ids and redo[0].layer_ids[0] == current_id and done:
                    operation = cross.peek_redo(current_id)
                    if coverage._run_is_next(done[-1], operation):
                        redo += (operation,)
            except (AttributeError, RuntimeError):
                pass
        return UndoFocus(KIND_VECTOR, undo, redo, undo_left, redo_left)

    # --- the tooltips and the panel -----------------------------------------------------

    def schedule_refresh(self, *_args) -> None:
        """Say again what Undo and Redo would do, and list the history again if it is open, once the buttons are set
        (the next pass of the event loop, once for a burst of changes)."""
        self._timer.start()

    def refresh(self) -> None:
        try:
            focus = self.focus()
        except Exception:  # whatever a history raises, the dock goes on: the tooltips stay as they were
            logger.warning("History: not read", exc_info=True)
            return
        self._show_tips(focus)
        if self.panel is not None and self.panel.isVisible():
            self._fill(focus)

    def _show_tips(self, focus: UndoFocus) -> None:
        for button, undo in zip((getattr(self._dock, UNDO_BUTTON, None), getattr(self._dock, REDO_BUTTON, None)),
                                (True, False)):
            if button is None:
                continue
            refs = focus.undo if undo else focus.redo
            try:
                label = label_of(refs[0]) if refs and button.isEnabled() else ""
                button.setToolTip(button_tip(undo, label, focus.kind, focus.undo_left if undo else focus.redo_left,
                                             focus.source))
            except RuntimeError:  # the dock is being deleted
                return

    def _fill(self, focus: UndoFocus) -> None:
        items = self.read()
        sources = {item.key: self._name(item.key) for item in items if item.kind == KIND_COVERAGE}
        self.panel.set_timeline(items, focus, sources)

    def _make_panel(self) -> HistoryPanel:
        if self.panel is None:
            self.panel = HistoryPanel(self._dock)
            self.panel.compare_button.clicked.connect(self.compare_selected)
            self.panel.pin_button.clicked.connect(self.pin_selected)
        return self.panel

    def _open_from_compare(self, *_args) -> None:
        self.open(getattr(self._compare, "button", None))

    def open(self, anchor=None) -> Optional[HistoryPanel]:
        """Show the history over the dock, above ``anchor`` (a button of the action bar); never modal."""
        panel = self._make_panel()
        try:
            self._fill(self.focus())
        except Exception:
            logger.warning("History: not read", exc_info=True)
            return None
        self._place(panel, anchor or getattr(self._dock, UNDO_BUTTON, None))
        panel.show()
        panel.raise_()
        panel.tree.setFocus()
        return panel

    def _place(self, panel: HistoryPanel, anchor) -> None:
        """Over the dock, its bottom on the top of ``anchor``, inside the screen."""
        dock = self._dock
        top_left = dock.mapToGlobal(QPoint(0, 0))
        bottom = anchor.mapToGlobal(QPoint(0, 0)).y() if anchor is not None else top_left.y() + dock.height()
        screen = QGuiApplication.screenAt(top_left) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry() if screen is not None else QRect(0, 0, 1600, 1000)
        width = min(max(dock.width(), PANEL_WIDTH), area.width() - 16)
        height = min(PANEL_HEIGHT, area.height() - 16)
        x = min(max(top_left.x(), area.left() + 8), area.right() - 8 - width)
        y = min(max(bottom - height, area.top() + 8), area.bottom() - 8 - height)
        panel.setGeometry(x, y, width, height)

    def close_panel(self, *_args) -> None:
        if self.panel is not None:
            try:
                self.panel.close()
            except RuntimeError:
                pass

    # --- the map before an item ---------------------------------------------------------

    def _selected(self) -> Optional[TimelineItem]:
        item = self.panel.selected() if self.panel is not None else None
        return item if item is not None and item.applied else None

    def compare_selected(self, *_args) -> int:
        """Compare the map now with the map before the selected item; the number of layers drawn otherwise."""
        item = self._selected()
        if item is None or self._compare is None:
            return 0
        before = map_before(self.panel.items, item)
        self.close_panel()
        text = _short(item.label)
        count = self._compare.compare_with(before, (_tr("Before: {}").format(text) if text else "", _tr("Now")))
        if not count and not self._compare.named:  # what it cannot draw is named instead
            self._say(_tr("Nothing to compare: nothing this step changed can be drawn."))
        return count

    def pin_selected(self, *_args):
        """Pin the map before the selected item: the map now, the layers changed since as they were then."""
        item = self._selected()
        if item is None or self._compare is None:
            return None
        before = map_before(self.panel.items, item)
        self.close_panel()
        from ...adapters.qgis.compare_swipe import map_state
        try:
            state = pin_before(map_state(self._canvas()), before, item.time)
        except Exception:  # whatever a layer raises: nothing is pinned, and the user is told
            logger.warning("History: map not pinned", exc_info=True)
            self._say(_tr("The map could not be pinned."))
            return None
        self._compare.pin_state(state)
        self._say(_tr("The map before this step is pinned: Compare shows it left of the line."))
        return state

    def _canvas(self):
        iface = getattr(self._dock, "iface", None)
        if iface is None:
            from qgis.utils import iface
        return iface.mapCanvas() if iface is not None else None

    def _say(self, text: str) -> None:
        try:
            from ...infrastructure.feedback import show_info
            show_info(text)
        except Exception:
            logger.debug("History: %s", text)

    def teardown(self) -> None:
        self._timer.stop()
        for signal, slot in self._connections:
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        self._connections = []
        for button in self.buttons:
            try:
                button.removeEventFilter(self)
            except RuntimeError:
                pass
        self.buttons = []
        if self.history_action is not None:
            try:
                self.history_action.triggered.disconnect(self._open_from_compare)
                menu = getattr(self._compare, "menu", None)
                if menu is not None:
                    menu.removeAction(self.history_action)
                    menu.removeAction(self._separator)
            except (TypeError, RuntimeError):
                pass
            self.history_action = self._separator = None
        self.close_panel()
