# -*- coding: utf-8 -*-
"""A section of the dock in its own QGIS panel.

* AGENT, FILTERING, EXPORTING and CONFIGURATION can each leave the dock for a panel of QGIS, which is dragged,
  tabbed with any other panel or floated as the user likes. EXPLORING stays: the dock is its panel, it holds the
  current layer the others work on.
* The widgets are those of the dock, moved: everything wired to them keeps working, nothing is kept in step. The
  section keeps its place in the tool box (its header hidden), so the indexes the code relies on do not move.
* The first time, FILTERING, EXPORTING and CONFIGURATION go below the dock, tabbed together; AGENT is tabbed with
  the dock. Afterwards QGIS puts each panel back where the user left it (it knows the panel by its object name).
* A section in its own panel takes its buttons with it (ui/layout/section_bars.py), and they act whatever is open
  in the dock. Closing the panel brings the section back to the dock, folded.
* Which sections are apart is kept in ``FilterMate/panels/detached`` and restored when the dock is built.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger("FilterMate")

DETACHABLE = ("agent", "filtering", "exporting", "configuration")
BOTTOM = ("filtering", "exporting", "configuration")  # the sections of the tool box, tabbed together when apart
TITLES = {"agent": "AGENT", "filtering": "FILTERING", "exporting": "EXPORTING", "configuration": "CONFIGURATION"}
SETTINGS_KEY = "FilterMate/panels/detached"
DOCK_AREA_KEY = "FilterMate/panels/dock_area"  # the area the dock was given the last time (DOCK_POSITION)
PANEL_NAME = "FilterMatePanel_{}"  # the object name of a panel: QGIS saves and restores its place under it
PANEL_MENU_NAME = "mPanelMenu"  # the menu View > Panels of QGIS
CONTENTS_NAME = "dockWidgetContents"  # the rules of the style sheets of the dock all start from this name
PANEL_MARGIN = 2  # as the contents of the dock


def parse_detached(value: Any) -> Tuple[str, ...]:
    """The sections apart, from the setting: known ones only, once each, in the order of the dock."""
    if isinstance(value, str):
        names = [name.strip().lower() for name in value.split(",")]
    elif isinstance(value, (list, tuple, set, frozenset)):
        names = [str(name).strip().lower() for name in value]
    else:
        return ()
    return tuple(key for key in DETACHABLE if key in names)


def format_detached(keys: Iterable[str]) -> str:
    return ",".join(parse_detached(list(keys)))


def remembered(detached: Iterable[str], saved: Iterable[str], present: Iterable[str]) -> Tuple[str, ...]:
    """What is kept as apart: the sections apart now, and those ``saved`` that the dock does not hold this time
    (AGENT turned off is not among those ``present``): they are apart again the day they come back."""
    now, before, here = set(detached), set(saved), set(present)
    return tuple(key for key in DETACHABLE if key in now or (key in before and key not in here))


def tab_partners(key: str, detached: Iterable[str]) -> List[str]:
    """The sections apart whose panel the new panel of ``key`` is tabbed with, the nearest first: FILTERING,
    EXPORTING and CONFIGURATION go together, AGENT with none of them."""
    if key not in BOTTOM:
        return []
    apart = [other for other in BOTTOM if other != key and other in set(detached)]
    rank = BOTTOM.index(key)
    return sorted(apart, key=lambda other: abs(BOTTOM.index(other) - rank))


PANEL_MIN_HEIGHT = 180
PANEL_MAX_SHARE = 0.55  # of the room the dock had: it keeps EXPLORING, which needs the larger part
TITLE_ROOM = 30  # the title bar of the panel, above its contents


def panel_height(hint: int, room: int, spare: int) -> int:
    """The height a panel gets when it is put below the dock for the first time, out of the ``room`` the dock had:
    what its section asks (``hint``), no less than a few rows, no more than its share nor than what the dock can
    ``spare`` above its own minimum. 0 when the dock has not that much to give: a sliver below it would be of no
    use, the panel is tabbed with it instead."""
    if spare < PANEL_MIN_HEIGHT:
        return 0
    return int(max(PANEL_MIN_HEIGHT, min(hint, room * PANEL_MAX_SHARE, spare)))


DOCK = "dock"  # in a menu, the FilterMate dock as the panel to group with


def menu_entries(key: str, detached: Iterable[str], present: Iterable[str] = DETACHABLE) -> List[Tuple[str, str]]:
    """What the menu of the section ``key`` offers, as ``(command, section)``, to separate, group and merge:

    * in the dock: ``detach`` (its own panel) when it can leave;
    * in its own panel: ``group`` with the dock (``DOCK``) and with each other panel, as tabs, then ``attach``
      (merged back into the dock);
    * ``detach_all`` when it would move another section than this one, ``attach_all`` when a section is apart.

    ``present``: the sections the dock has, in it or apart (a section turned off is not among them)."""
    apart = [name for name in DETACHABLE if name in set(detached)]
    in_dock = [name for name in DETACHABLE if name in set(present) and name not in apart]
    entries: List[Tuple[str, str]] = []
    if key in apart:
        entries += [("group", other) for other in [DOCK] + [name for name in apart if name != key]]
        entries.append(("attach", key))
    elif key in in_dock:
        entries.append(("detach", key))
    if [name for name in in_dock if name != key]:
        entries.append(("detach_all", ""))
    if apart:
        entries.append(("attach_all", ""))
    return entries


def restore_dock_first(detached: Iterable[str], saved_area: Any, area: Any) -> bool:
    """The dock goes back where QGIS remembers it, rather than at the end of the ``area`` of its setting, when
    sections were in their own panels the last time: QGIS keeps their places relative to it, and added again after
    them the dock came back below the panel that was under it. A change of ``DOCK_POSITION`` since wins: the dock
    goes to its new area (``saved_area`` is the one it was given the last time)."""
    return bool(tuple(detached)) and saved_area is not None and str(saved_area) == str(area)


def _tr(text: str) -> str:
    from qgis.PyQt.QtCore import QCoreApplication
    return QCoreApplication.translate("SectionPanels", text)


def _area_number(area: Any) -> int:
    """A Qt.DockWidgetArea as a number, in Qt5 (an int) and in Qt6 (an enum)."""
    return int(getattr(area, "value", area))


def _list_panel(window: Any, dock: Any) -> None:
    """``dock`` in the menu of the panels of QGIS, where ``iface.addDockWidget`` puts the docks it adds."""
    try:
        from qgis.PyQt.QtWidgets import QMenu
        menu = window.findChild(QMenu, PANEL_MENU_NAME)
        action = dock.toggleViewAction()
        if menu is not None and action not in menu.actions():
            menu.addAction(action)
    except Exception:  # nosec B110 - the panel is there, only not listed in the menu
        pass


def place_dock(dock: Any, iface: Any, area: Any) -> bool:
    """``dock`` in the main window of QGIS: where QGIS remembers it when sections were in their own panels the last
    time (``restore_dock_first``), else in ``area`` as ever. True when its place was restored."""
    restored = False
    try:
        from qgis.PyQt.QtCore import QSettings
        settings = QSettings()
        number = _area_number(area)
        if restore_dock_first(_saved(), settings.value(DOCK_AREA_KEY), number):
            window = iface.mainWindow()
            restored = bool(window.restoreDockWidget(dock))
            if restored:
                _list_panel(window, dock)
        settings.setValue(DOCK_AREA_KEY, number)
    except Exception:
        logger.debug("The place of the dock was not restored", exc_info=True)
    if not restored:
        iface.addDockWidget(area, dock)
    return restored


def _saved() -> Tuple[str, ...]:
    try:
        from qgis.PyQt.QtCore import QSettings
        return parse_detached(QSettings().value(SETTINGS_KEY, ""))
    except Exception:
        return ()


def _save(keys: Iterable[str]) -> None:
    try:
        from qgis.PyQt.QtCore import QSettings
        QSettings().setValue(SETTINGS_KEY, format_detached(keys))
    except Exception:  # nosec B110 - a convenience: the sections come back in the dock next time
        pass


def _panel_class():
    """A QGIS dock that says when the user closes it."""
    from qgis.PyQt.QtCore import pyqtSignal
    try:
        from qgis.gui import QgsDockWidget as Base
    except ImportError:
        from qgis.PyQt.QtWidgets import QDockWidget as Base

    class SectionPanel(Base):
        closed_by_user = pyqtSignal(str)

        def __init__(self, key: str, title: str, parent: Any) -> None:
            super().__init__(title, parent)
            self.key = key
            self.body = None
            self.scroll = None

        def closeEvent(self, event: Any) -> None:  # noqa: N802 - Qt name
            super().closeEvent(event)
            self.closed_by_user.emit(self.key)

    return SectionPanel


class SectionPanels:
    """The sections of ``dock`` shown in their own panel, and the way there and back."""

    def __init__(self, dock: Any, window: Any = None) -> None:
        from qgis.PyQt.QtCore import QObject
        self._dock = dock
        self._window = window
        self._panels: Dict[str, Any] = {}
        self._origins: Dict[str, Any] = {}  # the scroll area of the tool box a page came from
        self._dock_minimum: Optional[int] = None  # the minimum height of the display profile, while it is relaxed
        self._hidden_with_dock = False
        self._closing = False
        self._panel_class = _panel_class()
        owner = self

        class _Watch(QObject):
            def eventFilter(self, watched: Any, event: Any) -> bool:  # noqa: N802 - Qt name
                owner._on_event(watched, event)
                return False

        self._watch = _Watch(dock)
        sections = self._sections()
        if sections is not None:
            sections.raise_detached = self.raise_panel  # asked to open, a section apart shows its panel
            # Turned off, a section apart goes back to the dock first; it stays kept as apart, for when it returns.
            sections.bring_back = lambda key: self.attach(key, remember=False)
            sections.on_menu = self._on_chip_menu  # a right click on the chip of a section, in a rail of the dock
        contents = getattr(dock, CONTENTS_NAME, None)
        if contents is not None:
            contents.installEventFilter(self._watch)  # its style sheet changes with the theme
        dock.installEventFilter(self._watch)  # closed, then shown again: its panels follow
        toolbox = getattr(dock, "toolBox_tabTools", None)
        if toolbox is not None:
            toolbox.currentChanged.connect(self._on_bottom_changed)
        dock.destroyed.connect(self._on_dock_destroyed)

    # --- what is apart ------------------------------------------------------------

    def detached(self) -> Tuple[str, ...]:
        return tuple(key for key in DETACHABLE if key in self._panels)

    def panel(self, key: str) -> Any:
        return self._panels.get(key)

    def can_detach(self, key: str) -> bool:
        """The section is in the dock and can leave it."""
        if key not in DETACHABLE or key in self._panels:
            return False
        sections = self._sections()
        if sections is None:
            return False
        if key in BOTTOM:
            return self._page_area(key) is not None
        return key in getattr(sections, "_pages", {})

    # --- there --------------------------------------------------------------------

    def detach(self, key: str, remember: bool = True) -> bool:
        """``key`` in its own panel. False when it is not in the dock, or could not be moved."""
        if not self.can_detach(key):
            return False
        window = self._main_window()
        if window is None:
            return False
        try:
            panel = self._make_panel(key, window)
            moved = self._take_bottom(key, panel) if key in BOTTOM else self._take_top(key, panel)
            if not moved:
                panel.deleteLater()
                return False
            self._panels[key] = panel
            self._after_change()  # first: the dock folds what left, and says how much room it can spare
            self._place(key, panel, window)
            if remember:
                self._remember()
            return True
        except RuntimeError:  # the dock went away
            logger.debug("Section %s not detached: the dock went away", key, exc_info=True)
            return False
        except Exception:
            logger.exception("Section %s could not be shown in its own panel", key)
            if key in self._panels:  # half way there: back in the dock, rather than in a panel nobody placed
                self.attach(key, remember=False)
            return False

    def restore(self) -> List[str]:
        """The sections that were apart the last time, apart again: those that are in the dock by now (AGENT comes
        after the others). Called when the dock is built, and again when AGENT is installed."""
        restored: List[str] = []
        try:
            if self._dock.parentWidget() is None:
                return restored  # the dock is not in the window of QGIS yet: its panels are placed after it
        except RuntimeError:
            return restored
        for key in _saved():
            if key not in self._panels and self.detach(key, remember=False):
                restored.append(key)
        return restored

    def _make_panel(self, key: str, window: Any) -> Any:
        from qgis.PyQt.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget
        panel = self._panel_class(key, TITLES[key], window)
        panel.setObjectName(PANEL_NAME.format(key))
        # In the menu of the panels of QGIS, the name of a section alone would say little.
        panel.toggleViewAction().setText(f"FilterMate: {TITLES[key]}")
        holder = QWidget(panel)
        holder.setObjectName(CONTENTS_NAME)
        body = QVBoxLayout(holder)
        body.setContentsMargins(PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN)
        body.setSpacing(0)
        panel.body = body
        if key in BOTTOM:  # as in the tool box: the section scrolls when the panel is shorter than it
            scroll = QScrollArea(holder)
            scroll.setObjectName("scrollArea_section_panel")
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            body.addWidget(scroll, 1)
            panel.scroll = scroll
        panel.setWidget(holder)
        contents = getattr(self._dock, CONTENTS_NAME, None)
        if contents is not None:  # the background of the dock is painted from its style sheet, or not at all
            from qgis.PyQt.QtCore import Qt
            styled = Qt.WidgetAttribute.WA_StyledBackground
            holder.setAttribute(styled, contents.testAttribute(styled))
        self._style(panel)
        panel.closed_by_user.connect(self._on_panel_closed)
        # Its tab selected: Qt shows nothing again (the page behind a tab was never hidden), so the page is told.
        panel.visibilityChanged.connect(lambda visible, name=key: self._on_panel_visible(name, visible))
        shortcuts = getattr(self._dock, "keyboard_shortcuts_for", None)
        if callable(shortcuts):  # F5, Ctrl+Z and Ctrl+Y of the dock, with the focus in the panel
            panel.shortcuts = shortcuts(panel)
        from qgis.PyQt.QtCore import Qt as _Qt
        panel.setContextMenuPolicy(_Qt.ContextMenuPolicy.CustomContextMenu)  # group, merge: on its title
        panel.customContextMenuRequested.connect(lambda pos, name=key, host=panel: self._show_panel_menu(name, host, pos))
        return panel

    def find_children(self, *args: Any, **kwargs: Any) -> list:
        """What the panels hold, looked for as ``QObject.findChildren`` does: the widgets of a section apart are no
        longer children of the dock, whose passes of style, size and icons look for them through it."""
        from qgis.PyQt.QtCore import Qt
        direct = Qt.FindChildOption.FindDirectChildrenOnly
        for value in list(args) + list(kwargs.values()):
            try:
                if value == direct:
                    return []  # the direct children of the dock only: none of them is in a panel
            except Exception:  # nosec B112 - a value that cannot be compared is not the option
                continue
        found: list = []
        for panel in self._panels.values():
            try:
                found.extend(panel.findChildren(*args, **kwargs))
            except RuntimeError:  # a panel that is going away
                pass
        return found

    def _take_bottom(self, key: str, panel: Any) -> bool:
        from .section_bars import SECTION_PAGES
        area = self._page_area(key)
        sections = self._sections()
        if area is None or sections is None:
            return False
        toolbox = self._dock.toolBox_tabTools
        page = getattr(self._dock, SECTION_PAGES[key])
        index = toolbox.indexOf(page)
        if toolbox.currentWidget() is page:  # before its item is turned off: QToolBox would open the next section
            toolbox.setCurrentWidget(sections._nothing)
        toolbox.setItemEnabled(index, False)
        self._origins[key] = area
        area.takeWidget()
        panel.scroll.setWidget(page)
        page.show()
        sections.detached.add(key)
        return True

    def _take_top(self, key: str, panel: Any) -> bool:
        sections = self._sections()
        page = sections._pages.get(key)
        if page is None:
            return False
        was_open = sections.is_open(key)
        sections._top_layout.removeWidget(page)
        sections.detached.add(key)
        if was_open:
            sections.open_top("exploring")
        panel.body.addWidget(page, 1)
        page.show()
        return True

    def _place(self, key: str, panel: Any, window: Any) -> None:
        """Where QGIS remembers the panel; the first time, below the dock (tabbed with the panels of the sections
        that go with it), AGENT tabbed with the dock."""
        from qgis.PyQt.QtCore import Qt, QTimer
        # restoreDockWidget before any addDockWidget, which forgets the place QGIS kept. So not iface.addDockWidget:
        # the panel is listed in the menu of the panels by hand.
        _list_panel(window, panel)
        if window.restoreDockWidget(panel):
            panel.show()
            return
        dock = self._dock
        area = window.dockWidgetArea(dock)
        docked = area != Qt.DockWidgetArea.NoDockWidgetArea and not dock.isFloating()
        window.addDockWidget(area if docked else Qt.DockWidgetArea.RightDockWidgetArea, panel)
        partner = None
        for other in tab_partners(key, self.detached()):
            candidate = self._panels.get(other)
            if candidate is not None and not candidate.isFloating() and not candidate.isHidden():
                partner = candidate
                break
        wanted = self._height_below(panel) if partner is None and docked and key in BOTTOM else 0
        if partner is not None:
            window.tabifyDockWidget(partner, panel)
        elif wanted:  # the room of the dock shared: the section at its own height, the dock keeps the larger part
            room = dock.height()
            window.splitDockWidget(dock, panel, Qt.Orientation.Vertical)
            window.resizeDocks([dock, panel], [room - wanted, wanted], Qt.Orientation.Vertical)
        elif docked:
            window.tabifyDockWidget(dock, panel)
        panel.show()
        QTimer.singleShot(0, lambda: self.raise_panel(key))  # a new tab comes behind the others

    def _height_below(self, panel: Any) -> int:
        """The height ``panel`` gets below the dock, 0 when the dock cannot spare it (``panel_height``)."""
        dock = self._dock
        contents = dock.widget()
        if contents is not None and contents.layout() is not None:
            contents.layout().activate()  # the minimum of the dock without the section that just left it
        room = dock.height()
        spare = room - max(dock.minimumHeight(), dock.minimumSizeHint().height())
        return panel_height(panel.widget().sizeHint().height() + TITLE_ROOM, room, spare)

    def relax_dock(self, profile_applied: bool = False) -> None:
        """With FILTERING, EXPORTING or CONFIGURATION in its own panel, the dock needs less height than its display
        profile asks for all of them (600 px in the normal one): no minimum of its own, Qt then holds it to what
        its contents need. The profile's minimum comes back with the last of them. ``profile_applied``: the
        dimensions of a profile were just applied, the minimum of the dock is the one to give back."""
        try:
            dock = self._dock
            if any(key in BOTTOM for key in self._panels):  # AGENT alone apart leaves the dock as tall as ever
                if self._dock_minimum is None or profile_applied:
                    self._dock_minimum = dock.minimumHeight()  # once: afterwards Qt writes what the contents need
                if dock.minimumHeight() > 0:
                    dock.setMinimumHeight(0)
            elif self._dock_minimum is not None:
                dock.setMinimumHeight(self._dock_minimum)
                self._dock_minimum = None
        except RuntimeError:  # the dock went away
            pass

    # --- and back -----------------------------------------------------------------

    def attach(self, key: str, remember: bool = True) -> bool:
        """``key`` back in the dock, folded."""
        panel = self._panels.get(key)
        if panel is None:
            return False
        try:
            bars = self._bars()
            if bars is not None:
                bars.host(key, None)
            if key in BOTTOM:
                self._give_bottom(key, panel)
            else:
                self._give_top(key, panel)
        except RuntimeError:
            logger.debug("Section %s not brought back: the dock went away", key, exc_info=True)
        except Exception:
            logger.exception("Section %s could not be brought back to the dock", key)
        self._panels.pop(key, None)
        self._rescue(key, panel)
        self._drop(panel)
        try:
            self._after_change()
        except RuntimeError:
            pass
        except Exception:  # the plugin unloads, its controllers are gone: the other panels still have to go
            logger.debug("The dock was not refreshed after %s came back", key, exc_info=True)
        if remember:
            self._remember()
        return True

    def _present(self) -> List[str]:
        """The sections this dock has, in it or apart: not AGENT, FILTERING or EXPORTING when they are turned off."""
        from .section_bars import SECTION_PAGES
        sections = self._sections()
        pages = getattr(sections, "_pages", {}) if sections is not None else {}
        shown = getattr(sections, "section_shown", None)
        return [key for key in DETACHABLE
                if key in pages or (getattr(self._dock, SECTION_PAGES.get(key, ""), None) is not None
                                    and not (callable(shown) and shown(key) is False))]

    def _remember(self) -> None:
        _save(remembered(self.detached(), _saved(), self._present()))

    def attach_all(self, remember: bool = True) -> None:
        """Every section back in the dock. Remembered: none is kept as apart, not even one that is turned off
        now (it used to go back to its panel the day it was turned on again, against this last word)."""
        for key in self.detached():
            self.attach(key, remember)
        if remember:
            _save(())

    def sections_changed(self) -> None:
        """A section was turned on or off (dock_chrome.apply_section_options): the buttons, the stack below and
        the room of the dock follow, as after a section left or came back."""
        try:
            self._after_change()
        except RuntimeError:  # the dock went away
            pass

    def shutdown(self) -> None:
        """The plugin unloads: the sections go back to the dock and their panels go, what was apart stays saved."""
        self._closing = True
        self.attach_all(remember=False)

    def _give_bottom(self, key: str, panel: Any) -> None:
        from .section_bars import SECTION_PAGES
        page = getattr(self._dock, SECTION_PAGES[key])
        area = self._origins.pop(key, None)
        sections = self._sections()
        if sections is not None:
            sections.detached.discard(key)
        if panel.scroll is not None and panel.scroll.widget() is page:
            panel.scroll.takeWidget()
        if area is None:
            return
        area.setWidget(page)
        page.show()
        toolbox = self._dock.toolBox_tabTools
        toolbox.setItemEnabled(toolbox.indexOf(page), True)

    def _give_top(self, key: str, panel: Any) -> None:
        sections = self._sections()
        page = sections._pages.get(key)
        if page is None:
            return
        panel.body.removeWidget(page)
        sections._top_layout.insertWidget(sections._top_layout.indexOf(sections.top_rail) + 1, page, 1)
        page.hide()
        sections.detached.discard(key)

    def _rescue(self, key: str, panel: Any) -> None:
        """Nothing of the dock stays in a panel that goes away: left there, it would be deleted with it. What the
        way back did not take (it failed half way) waits hidden in the dock."""
        try:
            from .section_bars import SECTION_BUTTONS, SECTION_PAGES
            dock = self._dock
            sections = self._sections()
            page = (getattr(dock, SECTION_PAGES[key], None) if key in SECTION_PAGES
                    else getattr(sections, "_pages", {}).get(key))
            bars = self._bars()
            left = [page, bars.frame(key) if bars is not None else None]
            left += [getattr(dock, name, None) for name in SECTION_BUTTONS.get(key, ())]
            home = getattr(dock, CONTENTS_NAME, None) or dock
            for widget in left:
                if widget is None or not panel.isAncestorOf(widget):
                    continue
                logger.warning("FilterMate: %s was left in the panel of %s; kept in the dock, hidden",
                               widget.objectName(), key)
                if panel.scroll is not None and panel.scroll.widget() is widget:
                    panel.scroll.takeWidget()
                widget.setParent(home)
                widget.hide()
        except RuntimeError:  # the dock went away
            pass
        except Exception:
            logger.exception("The panel of %s could not be emptied", key)

    def _drop(self, panel: Any) -> None:
        try:
            panel.closed_by_user.disconnect(self._on_panel_closed)
        except (TypeError, RuntimeError):
            pass
        try:
            window = self._main_window()
            if window is not None:
                window.removeDockWidget(panel)
            panel.setParent(None)
            panel.deleteLater()
        except RuntimeError:
            pass

    # --- the dock around ----------------------------------------------------------

    def _after_change(self) -> None:
        """The buttons follow their section, the stacks of the dock take the room of what left or make room for
        what came back."""
        dock = self._dock
        manager = getattr(dock, "_action_bar_manager", None)
        if manager is not None:
            manager.sync_sections()
            bars = manager.section_bars()
            if bars is not None:
                for key, panel in self._panels.items():
                    bars.host(key, panel.body)
                bars.settle()
        select = getattr(dock, "select_tabTools_index", None)
        if callable(select) and not self._closing:  # not while the plugin unloads: its controllers are gone
            select()  # the buttons of a section apart act whatever is open in the dock
        self.relax_dock()
        sections = self._sections()
        if sections is not None:
            sections.refresh_rails()  # the chip of a section apart leaves its rail; with none left below, the
            # upper stack takes the dock

    def _bars(self) -> Any:
        manager = getattr(self._dock, "_action_bar_manager", None)
        return manager.section_bars() if manager is not None else None

    def _sections(self) -> Any:
        return getattr(self._dock, "_fm_sections", None)

    def _main_window(self) -> Any:
        if self._window is not None:
            return self._window
        try:
            from qgis.utils import iface
            return iface.mainWindow() if iface is not None else None
        except Exception:
            return None

    def _page_area(self, key: str) -> Any:
        """The scroll area QToolBox wraps the page of ``key`` in, None when the page is not in it."""
        from qgis.PyQt.QtWidgets import QScrollArea
        from .section_bars import SECTION_PAGES
        toolbox = getattr(self._dock, "toolBox_tabTools", None)
        page = getattr(self._dock, SECTION_PAGES.get(key, ""), None)
        if toolbox is None or page is None or toolbox.indexOf(page) < 0:
            return None
        if not toolbox.isItemEnabled(toolbox.indexOf(page)):
            return None  # a section turned off is not shown anywhere
        viewport = page.parentWidget()
        area = viewport.parentWidget() if viewport is not None else None
        return area if isinstance(area, QScrollArea) and area.widget() is page else None

    def raise_panel(self, key: str) -> None:
        panel = self._panels.get(key)
        if panel is None:
            return
        try:
            panel.show()
            panel.raise_()
        except RuntimeError:
            pass

    def _style(self, panel: Any) -> None:
        """The style sheet of the dock, on the contents of the panel (they bear the same name)."""
        contents = getattr(self._dock, CONTENTS_NAME, None)
        holder = panel.widget()
        if contents is None or holder is None:
            return
        sheet = contents.styleSheet()
        if holder.styleSheet() != sheet:
            holder.setStyleSheet(sheet)

    # --- events -------------------------------------------------------------------

    def _on_event(self, watched: Any, event: Any) -> None:
        from qgis.PyQt.QtCore import QEvent
        try:
            kind = event.type()
            if watched is getattr(self._dock, CONTENTS_NAME, None):
                if kind == QEvent.Type.StyleChange:
                    for panel in self._panels.values():
                        self._style(panel)
            elif watched is self._dock and kind == QEvent.Type.Close:
                self._on_dock_closed()  # the close event itself: the dock may not say that it closes
            elif watched is self._dock and kind == QEvent.Type.Show and self._hidden_with_dock:
                self._hidden_with_dock = False
                for panel in self._panels.values():
                    panel.show()
        except RuntimeError:
            pass

    def _on_dock_closed(self) -> None:
        """The dock is closed: the panels of its sections go with it, and come back when it is shown again. They
        are hidden, not closed: a panel the user closes brings its section back."""
        if not self._panels:
            return
        self._hidden_with_dock = True
        for panel in self._panels.values():
            try:
                panel.hide()
            except RuntimeError:
                pass

    def _on_dock_destroyed(self, *_args: Any) -> None:
        """The dock went without the plugin unloading it: its panels would stay in QGIS with nothing behind them."""
        self._closing = True
        panels, self._panels = self._panels, {}
        for panel in panels.values():
            self._drop(panel)

    def _on_panel_closed(self, key: str) -> None:
        if self._closing or key not in self._panels:
            return
        from qgis.PyQt.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._attach_closed(key))  # after the close event of the panel is over

    def _attach_closed(self, key: str) -> None:
        """The user closed the panel of ``key``: its section comes back. Not when QGIS itself is closing (a floating
        panel is closed with its windows): the section stays apart for the next time."""
        try:
            window = self._main_window()
            if self._closing or window is None or not window.isVisible():
                return
        except RuntimeError:
            return
        self.attach(key)

    def _on_panel_visible(self, key: str, visible: bool) -> None:
        """The panel of ``key`` comes in view (shown, or its tab selected): a page that tells when it is shown
        (AGENT: an offer waiting in its thread is seen then) says so, once Qt has laid the tabs out."""
        if not visible or key not in self._panels or self._closing:
            return
        from qgis.PyQt.QtCore import QTimer

        def tell() -> None:
            try:
                sections = self._sections()
                page = getattr(sections, "_pages", {}).get(key) if sections is not None else None
                shown = getattr(page, "shown", None)
                if key in self._panels and shown is not None and hasattr(shown, "emit") and sections.is_open(key):
                    shown.emit()
            except (RuntimeError, TypeError):  # the page went away
                pass
        QTimer.singleShot(0, tell)

    def _on_bottom_changed(self, index: int) -> None:
        """Something opened a section that is apart (a script, the agent): its panel comes forward instead."""
        from .section_bars import SECTION_PAGES
        try:
            page = self._dock.toolBox_tabTools.widget(index)
            for key in BOTTOM:
                if key in self._panels and page is getattr(self._dock, SECTION_PAGES[key], None):
                    self._dock.toolBox_tabTools.setCurrentWidget(self._sections()._nothing)
                    self.raise_panel(key)
                    return
        except (RuntimeError, AttributeError):
            pass

    # --- the menu of a section --------------------------------------------------------

    def _on_chip_menu(self, key: str, place: Any) -> None:
        """A right click on the chip of a section, in a rail of the dock."""
        self._popup(key, self._dock, place)

    def build_menu(self, key: str, parent: Any) -> Any:
        """The menu of the section ``key`` (on its header in the dock, on the title of its panel): separate, group,
        merge. None when it would be empty."""
        from qgis.PyQt.QtWidgets import QMenu
        entries = []
        for command, name in menu_entries(key, self.detached(), self._present()):
            if command == "detach" and not self.can_detach(name):
                continue
            if command == "group" and not self.can_group(key, name):
                continue
            entries.append((command, name))
        if not entries:
            return None
        texts = {
            "detach": lambda name: _tr("Open {} in its own panel").format(TITLES[name]),
            "detach_all": lambda name: _tr("Open every section in its own panel"),
            "group": lambda name: _tr("Group with {}").format("FilterMate" if name == DOCK else TITLES[name]),
            "attach": lambda name: _tr("Merge {} back into FilterMate").format(TITLES[name]),
            "attach_all": lambda name: _tr("Merge every section back into FilterMate"),
        }
        runs = {
            "detach": self.detach, "detach_all": lambda _name: self.detach_all(),
            "group": lambda name: self.group(key, name), "attach": self.attach,
            "attach_all": lambda _name: self.attach_all(),
        }
        menu = QMenu(parent)
        parts = {"detach": 0, "group": 0, "attach": 1, "detach_all": 2, "attach_all": 2}  # this section, then all
        before = None
        for command, name in entries:
            if before is not None and parts[command] != before:
                menu.addSeparator()
            action = menu.addAction(texts[command](name))
            action.setObjectName(f"action_section_{command}" + (f"_{name}" if command == "group" else ""))
            action.triggered.connect(lambda _checked=False, run=runs[command], name=name: run(name))
            before = parts[command]
        return menu

    def can_group(self, key: str, other: str) -> bool:
        """The panel of ``key`` can become a tab of the panel of ``other`` (``DOCK``: the dock): both are there, the
        other one is docked, and they are not tabbed together yet."""
        panel = self._panels.get(key)
        target = self._dock if other == DOCK else self._panels.get(other)
        window = self._main_window()
        if panel is None or target is None or window is None or target is panel:
            return False
        try:
            return (not target.isFloating() and not target.isHidden()
                    and panel not in window.tabifiedDockWidgets(target))
        except RuntimeError:
            return False

    def group(self, key: str, other: str) -> bool:
        """The panel of ``key`` as a tab beside the panel of ``other`` (``DOCK``: beside the dock)."""
        if not self.can_group(key, other):
            return False
        from qgis.PyQt.QtCore import QTimer
        panel = self._panels[key]
        target = self._dock if other == DOCK else self._panels[other]
        try:
            if panel.isFloating():
                panel.setFloating(False)
            self._main_window().tabifyDockWidget(target, panel)
            panel.show()
            QTimer.singleShot(0, lambda: self.raise_panel(key))  # a new tab comes behind the others
            return True
        except RuntimeError:
            return False

    def detach_all(self) -> List[str]:
        """Every section that can leave the dock, in its own panel; those that left.

        Each new tab comes in front of the one before: left alone, AGENT would hide the dock (EXPLORING) and
        CONFIGURATION would hide FILTERING. What was open stays in front: AGENT or the dock above, and below the
        section that was open, FILTERING when none was."""
        from qgis.PyQt.QtCore import QTimer
        from .section_bars import SECTION_PAGES
        sections = self._sections()
        agent_open = bool(sections is not None and sections.is_open("agent"))
        toolbox = getattr(self._dock, "toolBox_tabTools", None)
        current = toolbox.currentWidget() if toolbox is not None else None
        below = next((key for key in BOTTOM if current is not None
                      and current is getattr(self._dock, SECTION_PAGES[key], None)), "filtering")
        left = [key for key in DETACHABLE if key not in self._panels and self.detach(key)]
        if left:
            QTimer.singleShot(0, lambda: self._bring_forward(below, agent_open))  # after the raise of each new tab
        return left

    def _bring_forward(self, below: str, agent_open: bool) -> None:
        try:
            for key in (below, "filtering"):
                if key in self._panels:
                    self.raise_panel(key)
                    break
            if agent_open and "agent" in self._panels:
                self.raise_panel("agent")
            elif not self._dock.isFloating():
                self._dock.raise_()
        except RuntimeError:  # the dock went away
            pass

    def _popup(self, key: str, parent: Any, place: Any) -> None:
        """The menu of ``key`` at ``place`` of the screen; never modal: the headless checks reach this path."""
        try:
            menu = self.build_menu(key, parent)
            if menu is not None:
                menu.aboutToHide.connect(menu.deleteLater)
                menu.popup(place)
        except RuntimeError:
            pass

    def _show_panel_menu(self, key: str, panel: Any, pos: Any) -> None:
        """A right click on the title of a panel (not in its contents, which have their own menus)."""
        try:
            holder = panel.widget()
            if holder is not None and holder.geometry().contains(pos):
                return
            self._popup(key, panel, panel.mapToGlobal(pos))
        except RuntimeError:
            pass


def install_section_panels(dock: Any) -> Optional[SectionPanels]:
    """``dock._fm_panels``: its sections can go to their own panel. None when the dock has no sections to move."""
    if getattr(dock, "_fm_sections", None) is None:
        return None
    try:
        dock._fm_panels = SectionPanels(dock)
        return dock._fm_panels
    except Exception:
        logger.exception("The sections cannot be shown in their own panels")
        return None
