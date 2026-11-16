# -*- coding: utf-8 -*-
"""The buttons of the action bar, under the section they act in.

* FILTERING has Filter, Undo, Redo, Compare and Unfilter; EXPORTING has Export (and QFieldCloud, with its extension);
  CONFIGURATION has About. The dock already ties them: a button is on only while its section is open.
* ``ACTION_BAR_POSITION`` = ``sections``: no bar for all. Each section shows its own buttons at the bottom of the
  dock while it is open; with none open below (EXPLORING alone) there is no bar, and it gets its room. With AGENT
  open, the buttons of FILTERING show: Undo, Redo and Compare walk the steps of the agent then.
* A section in its own panel (ui/layout/section_panels.py) takes its buttons with it, whatever the position. The
  bar for all, left with the buttons of the other sections, shows only while one of them acts: not for an Export
  greyed out beside About.

The buttons are those of the form, moved from a bar to another: what is wired to them keeps working.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger("FilterMate")

SECTIONS_POSITION = "sections"
ONE_BAR = ""  # in a plan, the key of the bar for all
ACTION_ORDER = (
    "pushButton_action_filter", "pushButton_action_undo_filter", "pushButton_action_redo_filter",
    "pushButton_action_compare", "pushButton_action_unfilter", "pushButton_action_export",
    "pushButton_action_qfieldcloud", "pushButton_action_about",
)
SECTION_BUTTONS = {
    "filtering": ACTION_ORDER[:5],
    "exporting": ACTION_ORDER[5:7],
    "configuration": ACTION_ORDER[7:],
}
# The page of each section in the tool box of the dock (its attribute on the dock).
SECTION_PAGES = {"filtering": "FILTERING", "exporting": "EXPORTING", "configuration": "CONFIGURATION"}
# With AGENT open in the dock they walk the steps of the agent (FilterMateDockWidget.agent_has_focus).
AGENT_BUTTONS = ACTION_ORDER[1:4]
BAR_NAME = "frame_actions"  # the bars of the sections are named as the one bar: its style rules apply to them
GAP = "gap"  # in the signature of a row, a growing gap


def bar_plan(position: str, detached: Iterable[str] = (), off: Iterable[str] = ()) -> Dict[str, Tuple[str, ...]]:
    """Which bar holds each button: ``{section: names}`` for the sections that carry theirs, and ``ONE_BAR`` for the
    buttons left to the bar for all. Every section carries its own with ``sections``; a detached one always does.
    A section turned ``off`` (``APP.OPTIONS.<NAME>.enabled``) carries none: its buttons that stay in use (Undo,
    Redo and Compare walk the steps of the agent and open the history) are in the bar for all."""
    apart, gone = set(detached), set(off)
    plan = {key: names for key, names in SECTION_BUTTONS.items()
            if key not in gone and (position == SECTIONS_POSITION or key in apart)}
    lent = {name for names in plan.values() for name in names}
    plan[ONE_BAR] = tuple(name for name in ACTION_ORDER if name not in lent)
    return plan


def one_bar_serves(names: Iterable[str], open_key: Optional[str], off: Iterable[str] = (),
                   agent: bool = False) -> bool:
    """The bar for all is worth its room, once a section took its buttons to its own panel: one of the buttons
    left in it acts. A button acts while its section is the one open below, when its section is turned off (what
    stays of FILTERING: Undo, Redo and Compare) and, for these three, while ``agent`` walks its steps."""
    owners = {name: key for key, group in SECTION_BUTTONS.items() for name in group}
    gone = set(off)
    for name in names:
        key = owners.get(name)
        if key is None or key == open_key or key in gone or (agent and name in AGENT_BUTTONS):
            return True
    return False


def _rank(name: Optional[str]) -> int:
    return ACTION_ORDER.index(name) if name in ACTION_ORDER else len(ACTION_ORDER)


def insert_position(present: Sequence[Optional[str]], name: str) -> int:
    """Where the button ``name`` goes in a bar whose items are ``present`` (the name of a button, None for a gap):
    before the first button that comes after it in the order of the bar, else after the last button."""
    rank, last = _rank(name), -1
    for index, other in enumerate(present):
        if other is None:
            continue
        if _rank(other) > rank:
            return index
        last = index
    return last + 1


def row_signature(buttons: Sequence[Tuple[Any, bool]]) -> List[Any]:
    """The items of the row of a section: its buttons ``(button, shown)`` spread evenly, a gap before, between and
    after those shown (one alone is centred). A hidden button takes no gap."""
    signature: List[Any] = [GAP]
    for button, shown in buttons:
        signature.append(button)
        if shown:
            signature.append(GAP)
    return signature


def section_active(key: str, open_key: Optional[str], detached: Iterable[str] = ()) -> bool:
    """The buttons of the section ``key`` act: it is the one open below, or it is in its own panel."""
    return key == open_key or key in set(detached)


def _hidden_by_code(button: Any) -> bool:
    """Hidden on purpose (QFieldCloud without its extension), not by a change of parent."""
    if not button.isHidden():
        return False
    try:
        from qgis.PyQt.QtCore import Qt
        return bool(button.testAttribute(Qt.WidgetAttribute.WA_WState_ExplicitShowHide))
    except AttributeError:  # an attribute Qt may not publish: a hidden button stays hidden
        return True


class SectionBars:
    """A bar per section that carries its buttons; the one bar keeps the others."""

    def __init__(self, dock: Any, manager: Any = None) -> None:
        self._dock = dock
        self._manager = manager
        self._frames: Dict[str, Any] = {}
        self._hosted: Dict[str, Any] = {}  # the layout of the panel that shows the bar of a section
        self._parked: Dict[Any, bool] = {}  # buttons out of a section, on their way to the one bar: shown or not
        self._plan = bar_plan("bottom")
        self._position, self._off = "bottom", ()
        self._managed_one_bar = False
        self._watch: Any = None
        self._pending = False
        self._watch_bar(getattr(dock, BAR_NAME, None))

    # --- what the action bar manager asks -----------------------------------------

    def lent(self) -> set:
        """The names of the buttons the sections carry: not for the one bar."""
        return {name for key, names in self._plan.items() if key != ONE_BAR for name in names}

    def prepare(self, position: str, detached: Iterable[str] = (), off: Iterable[str] = ()) -> None:
        """The plan for ``position``: the buttons a section no longer carries leave its row, on their way to the one
        bar (``settle`` puts them there, unless the manager rebuilt it with them in between)."""
        self._plan = bar_plan(position, detached, off)
        self._position, self._off = position, tuple(off)
        one_bar = getattr(self._dock, BAR_NAME, None)
        for key, frame in self._frames.items():
            keep = self._buttons(self._plan.get(key, ()))
            row = frame.layout()
            for index in reversed(range(row.count())):
                widget = row.itemAt(index).widget()
                if widget is None or widget in keep:
                    continue
                self._parked[widget] = not _hidden_by_code(widget)
                row.removeWidget(widget)
                widget.setParent(one_bar)

    def settle(self) -> None:
        """Every section of the plan has its buttons in its row; those left go to the one bar, in its order."""
        try:
            for key in SECTION_BUTTONS:
                names = self._plan.get(key)
                if names:
                    self._fill(self._ensure_frame(key), self._buttons(names))
            self._return_parked()
            self._show()
        except RuntimeError:  # the dock went away
            logger.debug("Section bars not settled: the dock went away", exc_info=True)

    def sync(self, position: str, detached: Iterable[str] = (), off: Iterable[str] = ()) -> None:
        self.prepare(position, detached, off)
        self.settle()

    def host(self, key: str, layout: Any = None) -> None:
        """The bar of ``key`` at the bottom of ``layout`` (its own panel); back at the bottom of the dock with None."""
        if layout is None:
            self._hosted.pop(key, None)
        else:
            self._hosted[key] = layout
        frame = self._frames.get(key)
        if frame is not None:
            self._place(key, frame)

    def frame(self, key: str) -> Any:
        return self._frames.get(key)

    # --- a button that comes by another hand ---------------------------------------

    def _watch_bar(self, bar: Any) -> None:
        """Compare is made beside Redo and QFieldCloud after Export, both after the dock, each in the bar it finds
        its neighbour in (and it evens the gaps of that bar its own way): the rows are put right once it is done."""
        if bar is None:
            return
        if self._watch is None:
            from qgis.PyQt.QtCore import QEvent, QObject
            owner = self

            class _Watch(QObject):
                def eventFilter(self, _watched: Any, event: Any) -> bool:  # noqa: N802 - Qt name
                    if event.type() == QEvent.Type.ChildAdded:
                        owner._settle_later()
                    return False

            self._watch = _Watch(self._dock)
        bar.installEventFilter(self._watch)

    def _settle_later(self) -> None:
        if self._pending:
            return
        self._pending = True
        from qgis.PyQt.QtCore import QTimer
        QTimer.singleShot(0, self._settle_pending)

    def _settle_pending(self) -> None:
        self._pending = False
        self.settle()

    # --- the rows -----------------------------------------------------------------

    def _buttons(self, names: Iterable[str]) -> list:
        found = (getattr(self._dock, name, None) for name in names)
        return [button for button in found if button is not None]

    def _ensure_frame(self, key: str) -> Any:
        frame = self._frames.get(key)
        if frame is not None:
            return frame
        from qgis.PyQt.QtWidgets import QFrame, QHBoxLayout, QSizePolicy
        frame = QFrame(self._dock.dockWidgetContents)
        frame.setObjectName(BAR_NAME)
        frame.setProperty("fm_section", key)
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row = QHBoxLayout(frame)
        row.setSpacing(0)
        self._frames[key] = frame
        self._place(key, frame)
        self._watch_bar(frame)
        return frame

    def _place(self, key: str, frame: Any) -> None:
        home = self._hosted.get(key)
        if home is None:
            home = getattr(self._dock, "horizontalLayout_actions_container", None)
        if home is None or home.indexOf(frame) >= 0:
            return
        from .mockup_layout import _layout_holding
        parent = frame.parentWidget()
        held = _layout_holding(parent.layout(), frame) if parent is not None and parent.layout() is not None else None
        if held is not None:
            held.removeWidget(frame)
        home.addWidget(frame)

    def _size(self, frame: Any) -> None:
        """The height and margins of the one bar when it is horizontal."""
        manager = self._manager
        height = manager.horizontal_bar_height() if manager is not None else 42
        margins = manager.horizontal_bar_margins() if manager is not None else (8, 2, 8, 2)
        frame.setFixedHeight(height)
        frame.layout().setContentsMargins(*margins)

    def _fill(self, frame: Any, buttons: list) -> None:
        row = frame.layout()
        state = [(button, not _hidden_by_code(button)) for button in buttons]
        self._size(frame)
        if self._signature(row) == row_signature(state):
            return
        for button, _shown in state:
            if row.indexOf(button) < 0:
                self._take(button)
        while row.count():
            row.takeAt(0)
        row.addStretch(1)
        for button, shown in state:
            row.addWidget(button)
            button.setVisible(shown)
            if shown:
                row.addStretch(1)

    @staticmethod
    def _signature(row: Any) -> list:
        return [row.itemAt(index).widget() or GAP for index in range(row.count())]

    def _take(self, button: Any) -> None:
        """Out of the layout that holds it (the one bar, most of the time)."""
        self._parked.pop(button, None)
        parent = button.parentWidget()
        if parent is None or parent.layout() is None:
            return
        from .mockup_layout import _layout_holding
        layout = _layout_holding(parent.layout(), button)
        if layout is None:
            return
        layout.removeWidget(button)
        if parent is getattr(self._dock, BAR_NAME, None):
            self._even(layout)

    def _return_parked(self) -> None:
        """The buttons no section carries any more, in the one bar at their place."""
        parked, self._parked = self._parked, {}
        one_bar = getattr(self._dock, BAR_NAME, None)
        layout = one_bar.layout() if one_bar is not None else None
        if layout is None:
            return
        changed = False
        for name in self._plan[ONE_BAR]:
            button = getattr(self._dock, name, None)
            if button is None or button not in parked:
                continue
            if layout.indexOf(button) < 0:
                present = [getattr(layout.itemAt(index).widget(), "objectName", lambda: None)()
                           if layout.itemAt(index).widget() is not None else None for index in range(layout.count())]
                self._insert(layout, insert_position(present, name), button)
                changed = True
            button.setVisible(parked[button])
        if changed:
            self._even(layout)

    @staticmethod
    def _insert(layout: Any, index: int, button: Any) -> None:
        from qgis.PyQt.QtCore import Qt
        from qgis.PyQt.QtWidgets import QVBoxLayout
        if isinstance(layout, QVBoxLayout):  # the bar on a side of the dock
            layout.insertWidget(index, button, 0, Qt.AlignmentFlag.AlignHCenter)
        else:
            layout.insertWidget(index, button)

    @staticmethod
    def _even(layout: Any) -> None:
        from .action_bar_manager import even_action_spacing
        even_action_spacing(layout)

    # --- what is shown ------------------------------------------------------------

    def open_key(self) -> Optional[str]:
        """The section open below in the dock, None with none open."""
        toolbox = getattr(self._dock, "toolBox_tabTools", None)
        current = toolbox.currentWidget() if toolbox is not None else None
        for key, page in SECTION_PAGES.items():
            if current is not None and current is getattr(self._dock, page, None):
                return key
        return None

    def _agent_walks(self) -> bool:
        """AGENT is open in the dock: Undo, Redo and Compare walk its steps."""
        focus = getattr(self._dock, "agent_has_focus", None)
        try:
            return bool(focus()) if callable(focus) else False
        except RuntimeError:  # the dock went away
            return False

    def _show(self) -> None:
        """In the dock, the bar of the open section only, and the bar of FILTERING while AGENT is open (Undo, Redo
        and Compare walk its steps); in a panel, the bar of its section. The one bar is shown while it keeps a
        button, and once a section took its own to a panel, while one of those left acts."""
        open_key = self.open_key()
        agent = self._agent_walks()
        for key, frame in self._frames.items():
            carries = bool(self._plan.get(key)) and any(not button.isHidden() for button in
                                                         self._buttons(self._plan[key]))
            frame.setVisible(carries and (key in self._hosted or key == open_key
                                          or (agent and key == "filtering")))
        one_bar = getattr(self._dock, BAR_NAME, None)
        if one_bar is None:
            return
        if self.lent():
            self._managed_one_bar = True
            names = [name for name in self._plan[ONE_BAR] if getattr(self._dock, name, None) is not None]
            apart = self._position != SECTIONS_POSITION  # a section in its own panel, the others in the one bar
            one_bar.setVisible(bool(names) and (not apart or one_bar_serves(names, open_key, self._off, agent)))
        elif self._managed_one_bar:  # every button is back: the bar as it was
            self._managed_one_bar = False
            one_bar.setVisible(True)
