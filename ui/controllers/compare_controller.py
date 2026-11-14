# -*- coding: utf-8 -*-
"""The Compare button of the action bar: the map before the operation Undo would undo, or a pinned map, left of a line.

It reads the history Undo reads, chosen the same way (``FilterMateApp.update_undo_redo_buttons``): the turns of the
agent while AGENT is open, the history of the raster / point cloud source while one is current, the vector filters
of the dock otherwise, restricted to the layers Undo restores. It is available when Undo is, and ends with any
operation of the action bar, a change of the current layer or of project: what it shows is the state Undo would
bring back now.

A pin (right-click on the button) keeps the map as it is: while it is there, Compare shows that state instead, is
available without Undo, and follows the map through filters, undos and turns of the agent, compared again each time
the map is drawn; a change of project forgets it. ``adapters/qgis/compare_swipe.py`` draws.
"""
from __future__ import annotations

import logging
import time
from dataclasses import replace
from typing import Optional, Tuple

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QCoreApplication, QEvent, QObject, QPointF, QRectF, QSize, Qt, QTimer
from qgis.PyQt.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from qgis.PyQt.QtWidgets import QMenu, QPushButton

from ...adapters.qgis.compare_swipe import CompareSession, MapWatch, map_state
from ...core.domain.compare_states import (BeforeMap, MapState, from_cross_operation, map_from_history_entry,
                                           map_from_operation, map_from_pin)

logger = logging.getLogger("FilterMate.compare")

BUTTON_NAME = "pushButton_action_compare"
# Operations of the action bar: the state before changes with them, the comparison ends (without a pin).
ENDING_BUTTONS = ("pushButton_action_filter", "pushButton_action_undo_filter", "pushButton_action_redo_filter",
                  "pushButton_action_unfilter")
LABEL_LENGTH = 40  # the description of an operation, above the map
FOLLOW_DELAY_MS = 200  # a pin is compared again once the map is drawn and stays so


def _tr(text: str) -> str:
    return QCoreApplication.translate("FilterMateDockWidget", text)


def _clock(timestamp: float) -> str:
    return time.strftime("%H:%M", time.localtime(timestamp))


def compare_icon(size: int = 32, colour: QColor = QColor(90, 90, 90), pinned: bool = False) -> QIcon:
    """Half a frame filled, a line between the halves: the map before, the line, the map after; ``pinned``: a dot
    in the top right corner, a state is pinned."""
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
    if pinned:
        radius = size * 0.17
        painter.setPen(QPen(QColor(255, 255, 255), max(1.0, size / 22)))
        painter.setBrush(QColor(230, 120, 20))
        painter.drawEllipse(QPointF(size - radius - 1.0, radius + 1.0), radius, radius)
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
    """One button, its menu (pin the map, remove the pin) and the comparison it starts and stops."""

    def __init__(self, dockwidget, integration=None) -> None:
        super().__init__(dockwidget)
        self._dock = dockwidget
        self._integration = integration
        self.session: Optional[CompareSession] = None
        self._pin: Optional[MapState] = None
        self._given: Optional[BeforeMap] = None  # a step compared through compare_with, the pin aside
        self._watch = MapWatch(self)  # while a pin is compared: whether the map may have changed
        self._shown: Optional[BeforeMap] = None  # what the comparison draws, to draw again only what changed
        self._said: Tuple[str, ...] = ()  # the layers already said not to be drawn as they were
        self._follow_timer = QTimer(self)
        self._follow_timer.setSingleShot(True)
        self._follow_timer.setInterval(FOLLOW_DELAY_MS)
        self._follow_timer.timeout.connect(self._follow)
        self.menu: Optional[QMenu] = None
        self.pin_action = self.unpin_action = None
        self.button = self._make_button()
        self._undo = getattr(dockwidget, "pushButton_action_undo_filter", None)
        self._connections = []
        if self.button is None:
            return
        self._sync_button()
        if self._undo is not None:  # available when Undo is
            self._undo.installEventFilter(self)
        # A disabled button swallows its right-click (QAbstractButton): the menu opens from here, to pin all the same.
        self.button.installEventFilter(self)
        self._connect(getattr(dockwidget, "undoRedoStateRequested", None), self.refresh)
        self._connect(getattr(dockwidget, "currentLayerChanged", None), self._on_operation)
        for name in ENDING_BUTTONS:
            button = getattr(dockwidget, name, None)
            self._connect(button.clicked if button is not None else None, self._on_operation)
        self._connect(QgsProject.instance().cleared, self._on_project_cleared)

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
        button.setAccessibleName(_tr("Compare before and after the last filter"))
        index = layout.indexOf(redo)
        layout.insertWidget(index + 1, button, 0, layout.itemAt(index).alignment())
        button.toggled.connect(self._on_toggled)
        # No room for another button in the action bar: the pin is in the menu of this one.
        menu = QMenu(button)
        self.pin_action = menu.addAction(_tr("Pin the current state"))
        self.pin_action.triggered.connect(self.pin)
        self.unpin_action = menu.addAction(_tr("Remove the pin"))
        self.unpin_action.triggered.connect(self.unpin)
        self.menu = menu
        button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        button.customContextMenuRequested.connect(self._show_menu)
        setattr(self._dock, BUTTON_NAME, button)
        return button

    def _show_menu(self, pos=None) -> None:
        """The menu of the button, under the mouse (``pos`` in the coordinates of the button); never modal."""
        if self.menu is None or self.button is None:
            return
        self.menu.popup(self.button.mapToGlobal(pos if pos is not None else self.button.rect().center()))

    def _sync_button(self) -> None:
        """Available when Undo is or a state is pinned; its icon and tooltip say which it compares."""
        if self.button is None:
            return
        try:
            enabled = (self._pin is not None or self._given is not None or self._undo is None
                       or self._undo.isEnabled())
            self.button.setEnabled(enabled)
            self.button.setIcon(compare_icon(pinned=self._pin is not None))
            if self.unpin_action is not None:
                self.unpin_action.setEnabled(self._pin is not None)
            if self._pin is None:
                tip = (_tr("Compare: the map before the last filter left of the line, as it is on its right; "
                           "the line follows the mouse") + "\n" + _tr("Right-click to pin the current state."))
            else:
                tip = (_tr("Compare: the map pinned at {} left of the line, as it is on its right; "
                           "the line follows the mouse").format(_clock(self._pin.taken_at))
                       + "\n" + _tr("Right-click to pin again or remove the pin."))
            self.button.setToolTip(tip)
        except RuntimeError:  # the dock is being deleted
            return
        if not enabled:
            self.stop()

    def eventFilter(self, watched, event):  # noqa: N802 - Qt override
        try:
            if watched is self._undo and event.type() == QEvent.Type.EnabledChange and self.button is not None:
                self._sync_button()
            elif (watched is self.button and self.button is not None and event.type() == QEvent.Type.ContextMenu
                    and not self.button.isEnabled()):
                self._show_menu(event.pos())
                return True
        except RuntimeError:  # the dock is being deleted
            pass
        return False

    # --- which history -----------------------------------------------------------

    def last_operation(self) -> BeforeMap:
        """The map Undo would bring back now, from the history it reads, for the layers it restores."""
        dock = self._dock
        agent_focus = getattr(dock, "agent_has_focus", None)
        if callable(agent_focus) and agent_focus():
            from ...adapters.agent.turn_checkpoint import HISTORY_KEY
            from ...adapters.public_api.operations import _api_service
            stack = _api_service().history.undo_stack(HISTORY_KEY)
            return map_from_operation(stack[-1]) if stack else BeforeMap()
        coverage = getattr(self._integration, "coverage_controller", None) if self._integration is not None else None
        layer = getattr(coverage, "active_layer", None) if coverage is not None else None
        if layer is not None:
            try:
                operation = coverage.service.history.peek_undo(layer.id())
            except (AttributeError, RuntimeError):
                operation = None
            return map_from_operation(operation) if operation is not None else BeforeMap()
        current = getattr(dock, "current_layer", None)
        if current is None:
            return BeforeMap()
        # The app is ``filter_mate_app`` (the initializer of the plugin), ``app`` on the former path.
        app = getattr(dock, "filter_mate_app", None) or getattr(dock, "app", None)
        history = getattr(app, "history_manager", None) if app is not None else None
        entry = history.peek_undo() if history is not None else None
        before = BeforeMap()
        if entry is not None:
            # Undo restores the source, and the layers to filter when their button is on (_handle_undo_redo).
            restored = {current.id()}
            button = getattr(dock, "pushButton_checkable_filtering_layers_to_filter", None)
            if button is not None and button.isChecked():
                restored.update(dock.get_layers_to_filter() or [])
            before = map_from_history_entry(entry, restored)
        # A vector source also filters raster and point cloud targets: Undo replays that cross operation only when
        # it is the one the last run recorded (CoverageModeController, task 'undo') and the vector step is an entry
        # of this source (launchTaskEvent).
        if coverage is not None and entry is not None and entry.layer_ids and entry.layer_ids[0] == current.id():
            try:
                runs = (getattr(coverage, "_linked_runs", None) or {}).get(current.id()) or []
                operation = coverage.service.history.peek_undo(current.id())
                linked = bool(runs) and coverage._run_is_next(runs[-1], operation)
            except (AttributeError, RuntimeError):
                linked = False
            if linked:
                known = {state.layer_id for state in before.states}
                before = replace(before, states=before.states + tuple(
                    state for state in from_cross_operation(operation) if state.layer_id not in known))
        return before

    def before_map(self) -> BeforeMap:
        """What Compare draws left of the line now: the pinned map, or the map before the last operation."""
        if self._pin is not None:
            canvas = self._canvas()
            now = self._watch.read(canvas) if self._watch.watching else map_state(canvas)
            return map_from_pin(self._pin, now)
        return self.last_operation()

    def _canvas(self):
        iface = getattr(self._dock, "iface", None)
        if iface is None:
            from qgis.utils import iface
        return iface.mapCanvas() if iface is not None else None

    # --- the pin -----------------------------------------------------------------

    @property
    def pinned(self) -> Optional[MapState]:
        return self._pin

    @property
    def named(self) -> Tuple[str, ...]:
        """What the last comparison said it could not draw as it was (a layer removed since...)."""
        return self._said

    def _pinned_mode(self) -> bool:
        """The comparison shows the pin (not a step given by ``compare_with``) and follows the map."""
        return self._pin is not None and self._given is None

    def pin(self, *_args) -> Optional[MapState]:
        """Keep the map as it is now: Compare shows it until the pin is removed or the project changes."""
        try:
            state = map_state(self._canvas())
        except Exception:  # whatever a layer raises: nothing is pinned, and the user is told
            logger.warning("Compare: map not pinned", exc_info=True)
            self._say(_tr("The map could not be pinned."))
            return None
        self.pin_state(state)
        self._say(_tr("Map pinned at {}: Compare shows it left of the line.").format(_clock(state.taken_at)))
        return state

    def pin_state(self, state: MapState) -> None:
        """Pin ``state`` (``map_state()`` of the map now, or of a step kept elsewhere): Compare shows it from now on."""
        self._pin = state
        self._sync_button()
        if self.session is not None and self.session.active and self._given is None:
            self._watch.start(self._canvas())
            try:
                self._show(self.before_map(), quiet=True)
            except Exception:
                logger.warning("Compare: map not read", exc_info=True)
                self._fail()

    def unpin(self, *_args) -> None:
        """Forget the pin: Compare shows the map before the last operation again (when there is one)."""
        if self._pin is None:
            return
        self._pin = None
        self._follow_timer.stop()
        self._watch.stop()
        self._sync_button()
        if self.session is not None and self.session.active and self._given is None:
            self.start()

    def _on_project_cleared(self, *_args) -> None:
        self.stop()
        self._pin = None
        self._sync_button()

    # --- the comparison ----------------------------------------------------------

    def _on_toggled(self, on: bool) -> None:
        if on:
            self._said = ()  # a comparison asked again says again what it cannot draw
            self.start()
        else:
            self.stop()

    def _labels(self, before: BeforeMap) -> Tuple[str, str]:
        if before.pinned_at is not None:
            left = _tr("Pinned {}").format(_clock(before.pinned_at))
        else:
            text = " ".join((before.label or "").split())
            if len(text) > LABEL_LENGTH:
                text = text[:LABEL_LENGTH - 1].rstrip() + "…"
            left = _tr("Before: {}").format(text) if text else ""
        return left, _tr("Now")

    def _session(self, canvas) -> CompareSession:
        if self.session is None:
            self.session = CompareSession(canvas, self)
            self.session.ended.connect(self.stop)
            self._connect(canvas.mapCanvasRefreshed, self._on_map_drawn)
        return self.session

    def start(self) -> int:
        """Compare now; the number of layers drawn otherwise than now (0: nothing to compare, the button goes up;
        with a pin, the comparison stays on and fills in at the next change)."""
        canvas = self._canvas()
        if canvas is None:
            self._say(_tr("Nothing to compare: no filter to undo here."))
            self._set_checked(False)
            return 0
        self._given = None
        self._session(canvas)
        pinned = self._pin is not None
        if pinned:
            self._watch.start(canvas)
        try:
            before = self.before_map()
        except Exception:
            logger.warning("Compare: %s not read", "map" if pinned else "history", exc_info=True)
            if pinned:  # never "nothing changed" for a map that could not be read
                self._fail()
                return 0
            before = BeforeMap()  # a history that cannot be read compares nothing; the map is left alone
        count = self._show(before)
        if pinned:
            self._set_checked(True)
            return count
        if not count:
            if not self._said:  # a step whose changes cannot be drawn was named instead
                self._say(_tr("Nothing to compare: no filter to undo here."))
            self._set_checked(False)
        return count

    def compare_with(self, before: BeforeMap, labels: Optional[Tuple[str, str]] = None) -> int:
        """Compare with ``before`` (a step of the history, for instance), the pin aside: ended as the comparison with
        the last operation is (Filter, Undo, another current layer...). The number of layers drawn otherwise than now;
        0: nothing drawn, the comparison is off."""
        canvas = self._canvas()
        if canvas is None:
            return 0
        self._session(canvas)
        self._follow_timer.stop()
        self._watch.stop()
        self._given = before
        self._said = ()
        self._sync_button()  # available while it compares, Undo or not
        count = self._show(before, labels=labels)
        if count:
            self._set_checked(True)
        else:
            self.stop()
        return count

    def _names(self, before: BeforeMap, refused) -> Tuple[str, ...]:
        """What is not drawn as it was: layers removed since, changes the comparison does not draw, clones refused."""
        project = QgsProject.instance()
        names = list(before.missing)
        for kind, layer_id, name in before.unshown:
            if kind == "tree":
                names.append(_tr("layer tree"))
            elif kind == "project_crs":
                names.append(_tr("project CRS"))
            else:
                layer = project.mapLayer(layer_id) if layer_id else None
                names.append(layer.name() if layer is not None else (name or layer_id))
        names += list(refused)
        return tuple(dict.fromkeys(name for name in names if name))

    def _show(self, before: BeforeMap, quiet: bool = False, labels: Optional[Tuple[str, str]] = None) -> int:
        """Draw ``before`` left of the line; say what cannot be drawn as it was when that changed, and, with a pin,
        that nothing changed since it."""
        keep = self._pinned_mode()
        count = self.session.start(before, QgsProject.instance().mapLayers(), keep=keep,
                                   labels=labels or self._labels(before))
        self._shown = before if self.session.active else None
        names = self._names(before, self.session.refused)
        if names and names != self._said:
            self._say(_tr("Not drawn as they were: {}").format(", ".join(names)))
        self._said = names
        if keep and before.empty and not names and not quiet:
            self._say(_tr("Nothing changed since the pin."))
        return count

    def _fail(self) -> None:
        self.stop()
        self._say(_tr("Compare stopped: the map could not be read."))

    def _on_map_drawn(self) -> None:
        """The map was drawn: a pin is compared again if something may have changed, at most every FOLLOW_DELAY_MS
        (a throttle: refreshes closer than that, an animated symbol, would hold back a debounce for ever)."""
        if (self._pinned_mode() and self.session is not None and self.session.active and self._watch.dirty
                and not self._follow_timer.isActive()):
            self._follow_timer.start()

    def _follow(self) -> None:
        """A pin: compare the map again, and draw the map before again only when what differs changed."""
        if not self._pinned_mode() or self.session is None or not self.session.active or not self._watch.dirty:
            return
        try:
            before = self.before_map()
        except Exception:  # a comparison frozen on a map it cannot read would mislead: it stops, and says so
            logger.warning("Compare: map not read", exc_info=True)
            self._fail()
            return
        reordered, self._watch.reordered = self._watch.reordered, False
        if before != self._shown:
            self._show(before)
        elif reordered and not before.empty:  # the same differences in another order: drawn again
            self.session.render()

    def refresh(self) -> None:
        """AGENT opened or closed, a turn of the agent done or undone: compare against what Undo reads now (a pin
        follows the map by itself, a step given by ``compare_with`` ends)."""
        if self.session is None or not self.session.active or self._pinned_mode():
            return
        if self._given is not None:
            self.stop()
        else:
            self.start()

    def _on_operation(self, *_args) -> None:
        """Filter, Undo, Redo, Unfilter or another current layer: the state before is another one; a pin stays."""
        if not self._pinned_mode():
            self.stop()

    def stop(self, *_args) -> None:
        given, self._given = self._given, None
        self._follow_timer.stop()
        self._watch.stop()
        if self.session is not None:
            self.session.stop()
        self._shown = None
        self._set_checked(False)
        if given is not None:  # available because it compared: as Undo is again
            self._sync_button()

    def teardown(self) -> None:
        for signal, slot in self._connections:
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        self._connections = []
        self._follow_timer.stop()
        self._watch.stop()
        for watched in (self._undo, self.button):
            try:
                if watched is not None:
                    watched.removeEventFilter(self)
            except RuntimeError:
                pass
        if self.session is not None:
            self.session.close()
        self._pin = None
        self._given = None
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
