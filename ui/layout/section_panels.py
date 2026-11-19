# -*- coding: utf-8 -*-
"""The sections of the dock in panels of QGIS: separated, grouped, merged.

* Every section can leave the dock for a panel of QGIS, which is dragged, tabbed with the panels of QGIS or
  floated as the user likes. The last section of the dock stays in it: the dock is never left empty.
* EXPLORING leaves by its own menu entry, or dragged: "every section out" keeps it in the dock, which is then its
  panel. Its panel goes above the dock the first time: what it selects stays over FILTERING, which works on it.
  Away from FILTERING it shows a chooser of the current layer of its own (ui/widgets/layer_chooser_mirror.py).
* A panel holds one section or several. With several, it lists them in a rail as the dock does
  (ui/widgets/section_rail.py): one is open, its chips are dragged to put them in another order.
* Two panels of FilterMate put together merge: a panel dropped as a tab of another one gives it its sections, and
  dropped as a tab of the dock it gives them back to the dock. They are never two tabs side by side.
* A chip is dragged from a rail to another: onto a panel, its section joins it; onto the rail of its stack in the
  dock, it comes back; out of every panel, it gets a new one where it was dropped.
* Taken out without saying where, a section joins the panel that already holds sections of its stack (FILTERING,
  EXPORTING and CONFIGURATION go together, as in the dock), else it gets a new panel: below the dock when the dock
  can spare the height, beside it otherwise. Afterwards QGIS puts each panel back where the user left it (it
  knows a panel by its object name, that of its first section).
* The widgets are those of the dock, moved: everything wired to them keeps working, nothing is kept in step. The
  page of a section keeps its place in the tool box, so the indexes the code relies on do not move.
* A section in a panel takes its buttons with it (ui/layout/section_bars.py), and they act whatever is open in the
  dock. Closing a panel brings its sections back to the dock, folded.
* What is apart, and with what, is kept in ``FilterMate/panels/detached`` (``agent,filtering+exporting``) and
  restored when the dock is built.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger("FilterMate")

DETACHABLE = ("agent", "exploring", "filtering", "exporting", "configuration")
BOTTOM = ("filtering", "exporting", "configuration")  # the sections of the lower stack: they go together
STAYS = "exploring"  # the section "every section out" leaves in the dock, and the first to come back to an empty one
TITLES = {"agent": "AGENT", "exploring": "EXPLORING", "filtering": "FILTERING", "exporting": "EXPORTING",
          "configuration": "CONFIGURATION"}
SETTINGS_KEY = "FilterMate/panels/detached"
DOCK_AREA_KEY = "FilterMate/panels/dock_area"  # the area the dock was given the last time (DOCK_POSITION)
PANEL_NAME = "FilterMatePanel_{}"  # the object name of a panel: QGIS saves and restores its place under it
PANEL_MENU_NAME = "mPanelMenu"  # the menu View > Panels of QGIS
CONTENTS_NAME = "dockWidgetContents"  # the rules of the style sheets of the dock all start from this name
PANEL_MARGIN = 2  # as the contents of the dock
FUSION_SETTLE_MS = 400  # a dock dropped with the mouse is plugged at the end of an animation (about 200 ms)
PANEL_GAP = 8  # between the rail of a panel and its open section, as in the dock
Groups = Tuple[Tuple[str, ...], ...]


def parse_groups(value: Any) -> Groups:
    """The panels kept in the settings, each with its sections in their order: ``agent,filtering+exporting``. Known
    sections only, once each. A list holds one panel per item: its sections, or its text (``filtering+exporting``;
    a name alone is a panel of its own)."""
    if isinstance(value, str):
        names = [part.split("+") for part in value.split(",")]
    elif isinstance(value, (list, tuple, set, frozenset)):
        names = [list(part) if isinstance(part, (list, tuple)) else str(part).split("+") for part in value]
    else:
        return ()
    seen: set = set()
    groups: List[Tuple[str, ...]] = []
    for part in names:
        members = []
        for name in part:
            key = str(name).strip().lower()
            if key in DETACHABLE and key not in seen:
                seen.add(key)
                members.append(key)
        if members:
            groups.append(tuple(members))
    return tuple(groups)


def format_groups(groups: Iterable[Any]) -> str:
    return ",".join("+".join(group) for group in parse_groups(list(groups)))


def parse_detached(value: Any) -> Tuple[str, ...]:
    """The sections apart, whatever their panel, in the order of the dock."""
    apart = {key for group in parse_groups(value) for key in group}
    return tuple(key for key in DETACHABLE if key in apart)


def remembered(groups: Iterable[Sequence[str]], saved: Iterable[Sequence[str]], present: Iterable[str]) -> Groups:
    """What is kept: the panels as they are now, and each section ``saved`` as apart that the dock does not hold
    this time (AGENT turned off, or not installed yet, is not among those ``present``): it is apart again the day
    it comes back. It is kept with the sections it shared a panel with, at its place among them, when one of them
    is still in a panel; in a panel of its own otherwise."""
    now = [list(group) for group in parse_groups(list(groups))]
    apart = {key for group in now for key in group}
    here = set(present)
    alone: List[Tuple[str, ...]] = []
    for group in parse_groups(list(saved)):
        for position, key in enumerate(group):
            if key in apart or key in here:
                continue  # in a panel, or in the dock where the user put it back
            mates = [mate for mate in group if mate != key and mate in apart]
            host = next((panel for panel in now if mates and mates[0] in panel), None)
            if host is None:
                alone.append((key,))
                continue
            after = [mate for mate in group[position + 1:] if mate in host]
            host.insert(host.index(after[0]) if after else len(host), key)
            apart.add(key)
    return tuple(tuple(group) for group in now) + tuple(alone)


def can_leave(key: str, in_dock: Iterable[str]) -> bool:
    """``key`` may leave the dock: it is in it, and not alone there (the last section of the dock stays)."""
    here = list(in_dock)
    return key in here and len(here) > 1


def would_leave(in_dock: Iterable[str]) -> List[str]:
    """What "every section out" moves, among the sections ``in_dock``: all of them but EXPLORING, whose panel the
    dock then is; with EXPLORING already apart, all but the last one, which stays in the dock."""
    here = [key for key in DETACHABLE if key in set(in_dock)]
    return [key for key in here if key != STAYS] if STAYS in here else here[:-1]


def comes_back(detached: Iterable[str]) -> Optional[str]:
    """The section that comes back to a dock left with none: EXPLORING when it is apart, else the first one."""
    apart = [key for key in DETACHABLE if key in set(detached)]
    if STAYS in apart:
        return STAYS
    return apart[0] if apart else None


def smart_group(key: str, groups: Iterable[Sequence[str]]) -> Optional[str]:
    """The panel a section joins when it is taken out without saying where: the one that already holds a section
    of its stack (FILTERING, EXPORTING and CONFIGURATION go together, as in the dock), named by its first section.
    None: a new panel (AGENT, EXPLORING, or the first section of the lower stack to leave)."""
    if key not in BOTTOM:
        return None
    for group in groups:
        if key not in group and any(member in BOTTOM for member in group):
            return group[0]
    return None


def panel_title(members: Sequence[str]) -> str:
    return " · ".join(TITLES[key] for key in members if key in TITLES)


PANEL_MIN_HEIGHT = 180
EXPLORING_SHARE = 0.45  # of the room the dock had, for EXPLORING placed above it the first time
PANEL_MAX_SHARE = 0.55  # of the room the dock had: it keeps EXPLORING, which needs the larger part
TITLE_ROOM = 30  # the title bar of the panel, above its contents
FLOATING_SIZE = (360, 460)  # a panel made by a chip dropped out of every panel


def panel_height(hint: int, room: int, spare: int) -> int:
    """The height a panel gets when it is put below the dock for the first time, out of the ``room`` the dock had:
    what its section asks (``hint``), no less than a few rows, no more than its share nor than what the dock can
    ``spare`` above its own minimum. 0 when the dock has not that much to give: a sliver below it would be of no
    use, the panel goes beside the dock instead."""
    if spare < PANEL_MIN_HEIGHT:
        return 0
    return int(max(PANEL_MIN_HEIGHT, min(hint, room * PANEL_MAX_SHARE, spare)))


PANEL_SIZING_AUTO, PANEL_SIZING_MANUAL = "auto", "manual"  # APP.DOCKWIDGET.PANEL_SIZING
RIGID, ELASTIC, OTHER = "rigid", "elastic", "other"  # what a dock of a column does with more height (column_heights)


def panel_sizing(config_data: Any) -> str:
    """``APP.DOCKWIDGET.PANEL_SIZING``: ``manual`` when it says so, ``auto`` otherwise (the default, and a
    configuration written before the setting, which has none)."""
    try:
        node = config_data["APP"]["DOCKWIDGET"]["PANEL_SIZING"]
    except (KeyError, TypeError):
        return PANEL_SIZING_AUTO
    value = node.get("value") if isinstance(node, dict) else node
    manual = isinstance(value, str) and value.strip().lower() == PANEL_SIZING_MANUAL
    return PANEL_SIZING_MANUAL if manual else PANEL_SIZING_AUTO


def _spread(amount: int, weights: Sequence[float], minimums: Sequence[int]) -> List[int]:
    """``amount`` shared in proportion to ``weights``, none below its minimum (those that would be are held to it
    and the others share what is left); whole pixels that add up to ``amount``. The minimums alone when they ask
    for more than ``amount``."""
    count = len(weights)
    if amount <= sum(minimums):
        return list(minimums)
    shares: List[float] = [0.0] * count
    free = list(range(count))
    left = float(amount)
    while free:
        total = sum(weights[i] for i in free)
        held = [i for i in free if (left * weights[i] / total if total > 0 else left / len(free)) < minimums[i]]
        if not held:
            for i in free:
                shares[i] = left * weights[i] / total if total > 0 else left / len(free)
            break
        for i in held:
            shares[i] = minimums[i]
            left -= minimums[i]
        free = [i for i in free if i not in held]
    heights = [int(share) for share in shares]
    for i in sorted(range(count), key=lambda i: heights[i] - shares[i])[:amount - sum(heights)]:
        heights[i] += 1  # the pixels lost to rounding, to those that lost the most
    return heights


def column_heights(docks: Sequence[Tuple[str, int, int, int]], room: int) -> List[int]:
    """The heights of the docks of a column of the window of QGIS, top to bottom, that share ``room``. Each dock is
    ``(kind, minimum, need, weight)``:

    * ``RIGID``: a panel of FilterMate that has nothing to do with more height than it ``need``s (FILTERING or
      EXPORTING, their rows at their own height): it gets that height.
    * ``ELASTIC``: a panel of FilterMate that uses any height (EXPLORING, AGENT, CONFIGURATION): what the rigid ones
      leave goes to these, in proportion to their ``weight`` (the height they have: the share the user, or the first
      place of the panel, left them).
    * ``OTHER``: a panel of QGIS (Layers, Browser...), or a group of tabs: it keeps its height (its ``weight``) when
      an elastic one takes the rest; it takes it, the others of its kind in proportion to their heights, otherwise.

    Rigid panels alone in their column share it in proportion to their need: nothing else can take the room. None
    is given less than its ``minimum``; when the room is short, the rigid ones and the panels of QGIS give up height
    down to theirs, the elastic ones first."""
    count = len(docks)
    kinds = [dock[0] for dock in docks]
    minimums = [max(0, int(dock[1])) for dock in docks]
    wanted = [max(minimums[i], int(docks[i][2])) if kinds[i] == RIGID else 0 for i in range(count)]
    elastic = [i for i in range(count) if kinds[i] == ELASTIC]
    others = [i for i in range(count) if kinds[i] == OTHER]
    rigid = [i for i in range(count) if kinds[i] == RIGID]
    heights = [0] * count
    if not elastic and not others:
        for i, height in zip(rigid, _spread(room, [wanted[i] for i in rigid], [minimums[i] for i in rigid])):
            heights[i] = height
        return heights
    if elastic:
        receivers, weights, kept = elastic, [float(docks[i][3] or 0) for i in elastic], rigid + others
        for i in others:
            wanted[i] = max(minimums[i], int(docks[i][3] or 0))
    else:
        receivers, weights, kept = others, [float(docks[i][3] or 0) for i in others], rigid
    floor = sum(minimums[i] for i in receivers)
    held = room - floor  # what the rigid ones and the panels kept can have at most
    if sum(wanted[i] for i in kept) <= held:
        for i in kept:
            heights[i] = wanted[i]
    else:
        for i, height in zip(kept, _spread(max(0, held), [wanted[i] for i in kept], [minimums[i] for i in kept])):
            heights[i] = height
    rest = room - sum(heights[i] for i in kept)
    for i, height in zip(receivers, _spread(rest, weights, [minimums[i] for i in receivers])):
        heights[i] = height
    return heights


def column_of(index: int, rects: Sequence[Tuple[int, int, int, int]]) -> List[int]:
    """The docks stacked with ``rects[index]`` in one column of a dock area, top to bottom. ``rects``: ``(left, top,
    width, height)`` of the docks of the area. In the column: those whose width overlaps its own over more than half
    of the narrower one; of two side by side, the one that overlaps it more (a dock beside it is in another column,
    and a dock across both columns is in each)."""
    left, _top, width, _height = rects[index]
    found = []
    for other, (x, _y, w, _h) in enumerate(rects):
        overlap = min(x + w, left + width) - max(x, left)
        if 2 * overlap > min(w, width):
            found.append((other, overlap))
    kept: List[int] = []
    for other, _overlap in sorted(found, key=lambda item: (-item[1], item[0] != index)):
        y, h = rects[other][1], rects[other][3]
        if all(min(y + h, rects[mate][1] + rects[mate][3]) - max(y, rects[mate][1]) <= 0 for mate in kept):
            kept.append(other)
    return sorted(kept, key=lambda other: rects[other][1])


def floating_height(kind: str, minimum: int, need: int, current: int, hint: int, fresh: bool, available: int) -> int:
    """The height of a floating panel: what its section needs when it is rigid; elastic, the height it has when it
    was elastic already (the user may have sized it), else a comfortable one, no less than ``FLOATING_SIZE`` and what
    its contents ask for (``hint``). Never more than the screen has (``available``), nor less than its minimum."""
    if kind == RIGID:
        height = need
    elif fresh:
        height = max(current, FLOATING_SIZE[1], hint)
    else:
        height = current
    if available > 0:
        height = min(height, available)
    return max(minimum, height)


def floating_corner(corner: Tuple[int, int], size: Tuple[int, int], area: Tuple[int, int, int, int]) -> Tuple[int, int]:
    """The top left corner of a floating panel of ``size`` asked at ``corner``, brought back so that the panel is
    whole in ``area`` (left, top, right, bottom of the screen); its left and top first when it is larger than it."""
    left = max(area[0], min(corner[0], area[2] - size[0] + 1))
    top = max(area[1], min(corner[1], area[3] - size[1] + 1))
    return left, top


def menu_entries(key: str, groups: Iterable[Sequence[str]],
                 present: Iterable[str] = DETACHABLE) -> List[Tuple[str, str]]:
    """What the menu of the section ``key`` offers, as ``(command, name)``, to separate, group and merge:

    * ``detach``: its own panel (from the dock, where the last section stays, or out of a panel it shares);
    * ``group``: into another panel, named by its first section; the one ``smart_group`` gives comes first, before
      ``detach`` for a section of the dock: it is where the section goes when nothing says where;
    * ``attach``: merged back into the dock;
    * ``detach_all`` when it would take another section than this one out of the dock (EXPLORING is not one of
      them: the dock is then its panel), ``attach_all`` when a section is apart.

    ``present``: the sections the dock has, in it or apart (a section turned off is not among them)."""
    panels = parse_groups([list(group) for group in groups])
    home = next((group for group in panels if key in group), None)
    apart = [name for group in panels for name in group]
    in_dock = [name for name in DETACHABLE if name in set(present) and name not in apart]
    others = [group[0] for group in panels if group is not home]
    smart = smart_group(key, panels)
    join = [("group", anchor) for anchor in ([smart] if smart in others else []) + [a for a in others if a != smart]]
    entries: List[Tuple[str, str]] = []
    if home is None:
        if can_leave(key, in_dock):
            first = join[:1] if smart in others else []
            entries += first + [("detach", key)] + join[len(first):]
    else:
        if len(home) > 1:
            entries.append(("detach", key))
        entries += join
        entries.append(("attach", key))
    if [name for name in would_leave(in_dock) if name != key]:
        entries.append(("detach_all", ""))
    if apart:
        entries.append(("attach_all", ""))
    return entries


def fusion(order: Sequence[Any], tabbed: Sequence[Sequence[Any]], with_dock: Sequence[Any],
           mover: Any = None) -> Optional[Tuple[Any, Any]]:
    """Two panels of FilterMate put together merge. ``order``: the panels, the oldest first; ``tabbed``: for each
    one, the panels it is tabbed with; ``with_dock``: those tabbed with the dock. ``(source, target)`` of the first
    merge to do, target None for the dock; None when nothing is tabbed. The panel that was moved (``mover``) gives
    its sections to the one that was there, else the newer to the older."""
    for panel in order:
        if panel in with_dock:
            return panel, None
    for panel, mates in zip(order, tabbed):
        for other in mates:
            if other is panel or other not in order:
                continue
            newer = panel if order.index(panel) > order.index(other) else other
            source = mover if mover in (panel, other) else newer
            return source, (other if source is panel else panel)
    return None


def restore_dock_first(detached: Iterable[Any], saved_area: Any, area: Any) -> bool:
    """The dock goes back where QGIS remembers it, rather than at the end of the ``area`` of its setting, when
    sections were in panels the last time: QGIS keeps their places relative to it, and added again after them the
    dock came back below the panel that was under it. A change of ``DOCK_POSITION`` since wins: the dock goes to
    its new area (``saved_area`` is the one it was given the last time)."""
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
    """``dock`` in the main window of QGIS: where QGIS remembers it when sections were in panels the last time
    (``restore_dock_first``), else in ``area`` as ever. True when its place was restored."""
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


def _saved() -> Groups:
    try:
        from qgis.PyQt.QtCore import QSettings
        return parse_groups(QSettings().value(SETTINGS_KEY, ""))
    except Exception:
        return ()


def _save(groups: Iterable[Sequence[str]]) -> None:
    try:
        from qgis.PyQt.QtCore import QSettings
        QSettings().setValue(SETTINGS_KEY, format_groups(groups))
    except Exception:  # nosec B110 - a convenience: the sections come back in the dock next time
        pass


def _panel_class():
    """A QGIS dock that holds sections, lists them in a rail when they are several, and says when the user closes
    it or drops the chip of a section on it."""
    from qgis.PyQt.QtCore import pyqtSignal
    from qgis.PyQt.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget
    from ..widgets.section_rail import SECTION_MIME, TAKES_SECTIONS, make_rail
    try:
        from qgis.gui import QgsDockWidget as Base
    except ImportError:
        from qgis.PyQt.QtWidgets import QDockWidget as Base

    class SectionPanel(Base):
        closed_by_user = pyqtSignal(object)  # this panel
        section_dropped = pyqtSignal(str, object)  # the chip of a section dropped on this panel, out of its rail

        def __init__(self, parent: Any, accepts: Any, dark: Any) -> None:
            super().__init__("", parent)
            self.members: List[str] = []
            self._accepts = accepts
            self._boxes: Dict[str, Any] = {}
            self._pages: Dict[str, Any] = {}
            self._current: Optional[str] = None
            # The section QGIS keeps the place of the panel under, while it is not here yet (AGENT comes after the
            # others when the dock opens): named after the sections it has, the panel would get another place.
            self.kept_name: Optional[str] = None
            self.setProperty(TAKES_SECTIONS, True)  # it decides itself what a dragged chip does on it
            holder = QWidget(self)
            holder.setObjectName(CONTENTS_NAME)
            self.body = QVBoxLayout(holder)
            self.body.setContentsMargins(PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN, PANEL_MARGIN)
            self.body.setSpacing(PANEL_GAP)
            self.rail = make_rail(holder, accepts=lambda key: accepts(key, self), dark=dark)
            self.body.addWidget(self.rail)
            self.rail.hide()  # one section: the title of the panel names it
            self.rail.chosen.connect(self.open)
            self.setWidget(holder)
            self.setAcceptDrops(True)

        # --- its sections -------------------------------------------------------------

        def add(self, key: str, page: Any, scrollable: bool, index: Optional[int] = None) -> None:
            """``page`` as the section ``key`` of the panel, at ``index`` of its rail (last without one); it is the
            open one: the section that just came is the one looked at."""
            box = QWidget(self.widget())
            box.setObjectName("widget_section_box")
            column = QVBoxLayout(box)
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(0)
            if scrollable:  # as in the tool box: the section scrolls when the panel is shorter than it
                scroll = QScrollArea(box)
                scroll.setObjectName("scrollArea_section_panel")
                scroll.setWidgetResizable(True)
                scroll.setFrameShape(QFrame.Shape.NoFrame)
                scroll.setWidget(page)
                column.addWidget(scroll, 1)
            else:
                column.addWidget(page, 1)
            page.show()
            self.body.addWidget(box, 1)
            self._boxes[key] = box
            self._pages[key] = page
            members = [name for name in self.members if name != key]
            at = len(members) if index is None else max(0, min(index, len(members)))
            self.members = members[:at] + [key] + members[at:]
            self.rail.set_sections(self.members)
            self.open(key)

        def take(self, key: str) -> Any:
            """The page of ``key``, out of the panel (the bar of its buttons left before); None when it is not here."""
            page = self._pages.pop(key, None)
            box = self._boxes.pop(key, None)
            if page is None or box is None:
                return None
            viewport = page.parentWidget()
            area = viewport.parentWidget() if viewport is not None else None
            if isinstance(area, QScrollArea) and area.widget() is page and box.isAncestorOf(area):
                area.takeWidget()
            elif box.isAncestorOf(page):  # not a page that was already put elsewhere (a move that failed half way)
                box.layout().removeWidget(page)
                page.setParent(None)
            self.body.removeWidget(box)
            box.setParent(None)
            box.deleteLater()
            self.members = [name for name in self.members if name != key]
            self.rail.set_sections(self.members)
            if self._current == key:
                self._current = None
                if self.members:
                    self.open(self.members[0])
            else:
                self.open(self._current)
            return page

        def open(self, key: Optional[str]) -> None:
            """The section ``key`` shown, the others folded; the rail is there with several sections."""
            if key not in self._boxes:
                key = self.members[0] if self.members else None
            self._current = key
            for name, box in self._boxes.items():
                box.setVisible(name == key)
            self.rail.set_current(key)
            self.rail.setVisible(len(self.members) > 1)

        def current(self) -> Optional[str]:
            return self._current

        def page(self, key: str) -> Any:
            return self._pages.get(key)

        def box_layout(self, key: str) -> Any:
            """The column of ``key``: its page, then the bar of its buttons."""
            box = self._boxes.get(key)
            return box.layout() if box is not None else None

        def set_order(self, order: Sequence[str]) -> None:
            self.members = [key for key in order if key in self._boxes] + [
                key for key in self.members if key not in order]

        def retitle(self) -> None:
            """Named after its sections; QGIS keeps its place under the name of the first one (``kept_name`` until
            that section is here)."""
            if not self.members:
                return
            if self.kept_name in self.members:
                self.kept_name = None
            title = panel_title(self.members)
            self.setWindowTitle(title)
            self.setObjectName(PANEL_NAME.format(self.kept_name or self.members[0]))
            # In the menu of the panels of QGIS, the name of a section alone would say little.
            self.toggleViewAction().setText(f"FilterMate: {title}")

        # --- events -------------------------------------------------------------------

        def closeEvent(self, event: Any) -> None:  # noqa: N802 - Qt name
            super().closeEvent(event)
            self.closed_by_user.emit(self)

        def _dragged(self, event: Any) -> Optional[str]:
            mime = event.mimeData()
            if mime is None or not mime.hasFormat(SECTION_MIME):
                return None
            key = bytes(mime.data(SECTION_MIME)).decode("utf-8")
            return key if self._accepts(key, self) else None

        def dragEnterEvent(self, event: Any) -> None:  # noqa: N802 - Qt name
            if self._dragged(event) is not None:
                event.acceptProposedAction()

        def dragMoveEvent(self, event: Any) -> None:  # noqa: N802 - Qt name
            if self._dragged(event) is not None:
                event.acceptProposedAction()

        def dropEvent(self, event: Any) -> None:  # noqa: N802 - Qt name
            key = self._dragged(event)
            if key is not None:
                event.acceptProposedAction()
                self.section_dropped.emit(key, self)

    return SectionPanel


class SectionPanels:
    """The sections of ``dock`` shown in panels, and the ways there, between them and back."""

    def __init__(self, dock: Any, window: Any = None) -> None:
        from qgis.PyQt.QtCore import QObject
        self._dock = dock
        self._window = window
        self._panels: List[Any] = []  # the oldest first
        self._home: Dict[str, Any] = {}  # the panel each section apart is in
        self._origins: Dict[str, Any] = {}  # the scroll area of the tool box a page came from
        self._dock_minimum: Optional[int] = None  # the minimum height the display profile gave the dock
        self._dock_relaxed = False  # the dock has no minimum of its own for now
        self._hidden_with_dock = False
        self._closing = False
        self._fusing = False
        self._fusion_pending = False
        self._restoring = False  # the places and sizes QGIS kept are taken as they are
        self._resize_pending = False
        self._resize_all = False  # every panel of FilterMate and its column is sized at the next pass (resize_soon)
        self._resize_only: List[Any] = []  # else these only (a panel placed while the others are restored)
        self._elastic: set = set()  # the dock and the panels that were elastic at the last pass
        self._press_signature: Any = None  # where the panels were when a mouse button was pressed on one of them
        self._panel_class = _panel_class()
        owner = self

        class _Watch(QObject):
            def eventFilter(self, watched: Any, event: Any) -> bool:  # noqa: N802 - Qt name
                return bool(owner._on_event(watched, event))

        self._watch = _Watch(dock)
        dock.setAcceptDrops(True)  # the chip of a section apart dropped anywhere on the dock: it comes back
        from ..widgets.section_rail import TAKES_SECTIONS
        dock.setProperty(TAKES_SECTIONS, True)  # so the drop is the dock's to take, not the rail's it comes from
        sections = self._sections()
        if sections is not None:
            sections.raise_detached = self.raise_panel  # asked to open, a section apart shows its panel
            # Turned off, a section apart goes back to the dock first; it stays kept as apart, for when it returns.
            sections.bring_back = lambda key: self.attach(key, remember=False)
            sections.on_menu = self._on_chip_menu  # a right click on the chip of a section, in a rail of the dock
            sections.on_dropped = lambda key, _index: self.attach(key)  # a chip of a panel dropped on a rail of the dock
            sections.on_dropped_out = self._on_dropped_out  # a chip of the dock dropped out of every rail and panel
            sections.on_user_open = self._on_dock_opened  # the user opened another section in the dock
        contents = getattr(dock, CONTENTS_NAME, None)
        if contents is not None:
            contents.installEventFilter(self._watch)  # its style sheet changes with the theme
        dock.installEventFilter(self._watch)  # closed, then shown again: its panels follow
        toolbox = getattr(dock, "toolBox_tabTools", None)
        if toolbox is not None:
            toolbox.currentChanged.connect(self._on_bottom_changed)
        # The dock dropped as a tab of one of its panels. Dragged with the mouse within its area, a docked dock
        # says neither signal: only the one that goes behind the new tab says it is hidden (visibilityChanged).
        for signal in ("topLevelChanged", "dockLocationChanged", "visibilityChanged"):
            getattr(dock, signal).connect(lambda *_args: self._moved(dock))
        for signal in ("topLevelChanged", "dockLocationChanged"):  # floated, docked, put in another area
            getattr(dock, signal).connect(lambda *_args: self._resize_soon(late=True))
        dock.destroyed.connect(self._on_dock_destroyed)

    # --- what is apart ------------------------------------------------------------

    def detached(self) -> Tuple[str, ...]:
        return tuple(key for key in DETACHABLE if key in self._home)

    def groups(self) -> Groups:
        """The panels, each with its sections in the order of its rail."""
        return tuple(tuple(panel.members) for panel in self._panels)

    def kept_apart(self) -> Groups:
        """The panels kept for the next time, each with its sections: those of now, and each section that was
        apart and is turned off, in a panel of its own."""
        return _saved()

    def keep_apart(self, groups: Iterable[Any]) -> None:
        """Keep exactly ``groups`` for the next time (the setup puts back what it found, a section turned off
        included). A name alone is a panel of its own."""
        _save(parse_groups(list(groups)))

    def panel(self, key: str) -> Any:
        """The panel that holds the section ``key``, None when it is in the dock."""
        return self._home.get(key)

    def can_detach(self, key: str) -> bool:
        """The section is in the dock and can leave it: not the last one, the dock is never left empty."""
        if key not in DETACHABLE or key in self._home:
            return False
        sections = self._sections()
        if sections is None:
            return False
        if not can_leave(key, self.in_dock()):
            return False
        if key in BOTTOM:
            return self._page_area(key) is not None
        return key in getattr(sections, "_pages", {})

    def in_dock(self) -> Tuple[str, ...]:
        """The sections the dock shows itself: those it has that are neither turned off nor in a panel."""
        return tuple(key for key in self._present() if key not in self._home)

    def keep_one_in_dock(self) -> Optional[str]:
        """A section was turned off and the dock is left with none: one comes back from its panel, EXPLORING
        first. The section brought back, None when the dock needed none."""
        if self._closing or not self._home or self.in_dock():
            return None
        key = comes_back(self.detached())
        if key is not None and self.attach(key):
            return key
        return None

    def can_take(self, key: str, panel: Any) -> bool:
        """``panel`` takes the section ``key``: one that can leave the dock, or one of another panel."""
        if key not in DETACHABLE or panel not in self._panels:
            return False
        home = self._home.get(key)
        return self.can_detach(key) if home is None else home is not panel

    # --- out of the dock, between panels, back --------------------------------------

    def detach(self, key: str, remember: bool = True, place: Any = None, named: Optional[str] = None) -> bool:
        """``key`` in a panel of its own: out of the dock, or out of a panel it shares. ``place`` (of the screen):
        the panel floats there. ``named``: the section QGIS keeps the place of the panel under, when it is another
        one (the first of a group, which is not there yet). False when the section cannot move."""
        if key in self._home:
            return self._split(key, remember, place)
        if not self.can_detach(key):
            return False
        window = self._main_window()
        if window is None:
            return False
        try:
            panel = self._new_panel(window)
            page = self._out_of_dock(key)
            if page is None:
                self._forget(panel)
                return False
            panel.add(key, page, key in BOTTOM)
            self._home[key] = panel
            panel.kept_name = named if named != key else None
            panel.retitle()
            self._unpin(key, panel)
            self._after_change()  # first: the dock folds what left, and says how much room it can spare
            self._place(panel, window, place)
            if remember:
                self._remember()
            return True
        except RuntimeError:  # the dock went away
            logger.debug("Section %s not detached: the dock went away", key, exc_info=True)
            return False
        except Exception:
            logger.exception("Section %s could not be shown in its own panel", key)
            self._bring_home(key)
            return False

    def move(self, key: str, panel: Any, index: Optional[int] = None, remember: bool = True,
             front: bool = True) -> bool:
        """``key`` into ``panel``, at ``index`` of its rail: from the dock, or from another panel (which goes when
        it gave its last section). ``front``: the panel comes in front of the tabs it shares, with ``key`` open."""
        if not self.can_take(key, panel):
            return False
        source = self._home.get(key)
        try:
            if source is None:
                page = self._out_of_dock(key)
            else:
                self._unhost(key)
                page = source.take(key)
            if page is None:
                return False
            panel.add(key, page, key in BOTTOM, index)
            self._home[key] = panel
            panel.retitle()
            self._unpin(key, panel)
            if source is not None:
                self._settle_panel(source)
            self._after_change()
            if front:
                self.raise_panel(key)
            if remember:
                self._remember()
            return True
        except RuntimeError:
            logger.debug("Section %s not moved: the dock went away", key, exc_info=True)
            return False
        except Exception:
            logger.exception("Section %s could not be moved to another panel", key)
            self._bring_home(key)
            return False

    def _unpin(self, key: str, holder: Any) -> None:
        """``key`` is in ``holder`` now: no other panel waits for it under its name."""
        for panel in self._panels:
            if panel is not holder and panel.kept_name == key:
                panel.kept_name = None
                panel.retitle()

    def _page(self, key: str) -> Any:
        from .section_bars import SECTION_PAGES
        if key in SECTION_PAGES:
            return getattr(self._dock, SECTION_PAGES[key], None)
        sections = self._sections()
        return getattr(sections, "_pages", {}).get(key) if sections is not None else None

    def _bring_home(self, key: str) -> None:
        """A move failed half way: the section goes back to the dock, rather than stay nowhere, or in a panel
        nobody placed."""
        from qgis.PyQt.QtWidgets import QScrollArea
        try:
            try:
                self._unhost(key)
            except RuntimeError:
                raise
            except Exception:
                logger.debug("The buttons of %s were not taken out of its panel", key, exc_info=True)
            self._home.pop(key, None)
            page = self._page(key)
            for panel in list(self._panels):
                if key in panel.members:
                    panel.take(key)
            sections = self._sections()
            left = key in self._origins if key in BOTTOM else (sections is not None and key in sections.detached)
            if page is not None and left:
                viewport = page.parentWidget()
                area = viewport.parentWidget() if viewport is not None else None
                if isinstance(area, QScrollArea) and area.widget() is page and area is not self._origins.get(key):
                    area.takeWidget()  # of a panel that goes: the page would be deleted with it
                self._into_dock(key, page)
            for panel in list(self._panels):
                self._rescue(key, panel)
                self._settle_panel(panel)
            self._after_change()
        except RuntimeError:  # the dock went away
            pass
        except Exception:
            logger.exception("Section %s could not be brought back to the dock", key)

    def group(self, key: str, anchor: str) -> bool:
        """``key`` into the panel that holds the section ``anchor``."""
        return self.move(key, self._home.get(anchor))

    def open_smart(self, key: str) -> bool:
        """``key`` out of the dock without saying where: into the panel that holds sections of its stack, else in
        a new one (``smart_group``)."""
        anchor = smart_group(key, self.groups())
        return self.group(key, anchor) if anchor is not None else self.detach(key)

    def arrange(self, groups: Iterable[Sequence[str]], remember: bool = True) -> bool:
        """The panels as ``groups`` says: each group in one panel, its sections in that order, every other section
        back in the dock (the setup puts the sections back where it found them). A section that cannot move (it
        is turned off) stays where it is. True when a section moved."""
        wanted = parse_groups([list(group) for group in groups])
        before = self.groups()
        placed = {key for group in wanted for key in group}
        for key in self.detached():
            if key not in placed:
                self.attach(key, remember=False)
        for group in wanted:
            panel = None
            for key in group:
                home = self._home.get(key)
                if panel is None:  # the first one that can be apart gives the group its panel
                    if (home is None or any(member not in group for member in home.members)) \
                            and not self.detach(key, remember=False):
                        continue
                    panel = self._home.get(key)
                elif home is not panel:
                    self.move(key, panel, remember=False)
            try:
                order = [key for key in group if panel is not None and key in panel.members]
                if panel is not None and order != list(panel.members):
                    shown = panel.current()
                    panel.set_order(order)
                    panel.rail.set_sections(panel.members)
                    panel.open(shown)
                    panel.retitle()
            except RuntimeError:  # the panel went away
                pass
        if remember:
            self._remember()
        return self.groups() != before

    def detach_all(self) -> List[str]:
        """Every section that can leave the dock, taken out: FILTERING, EXPORTING and CONFIGURATION together, as in
        the dock, AGENT in its own panel. EXPLORING stays: the dock is then its panel (it leaves by its own menu
        entry, on purpose); with EXPLORING already apart, the last section stays. Those that left.

        A section that joins a panel is the one it shows, and a place QGIS kept may be behind another tab. What
        was open stays in view: below the section that was open, FILTERING when none was; above AGENT when it
        was, the dock (EXPLORING) otherwise."""
        from qgis.PyQt.QtCore import QTimer
        from .section_bars import SECTION_PAGES
        sections = self._sections()
        agent_open = bool(sections is not None and sections.is_open("agent"))
        try:  # behind the tab of another panel of QGIS (Layers), the dock stays there
            dock_front = self._dock.isVisible() and not self._dock.visibleRegion().isEmpty()
        except RuntimeError:
            dock_front = False
        toolbox = getattr(self._dock, "toolBox_tabTools", None)
        current = toolbox.currentWidget() if toolbox is not None else None
        below = next((key for key in BOTTOM if current is not None
                      and current is getattr(self._dock, SECTION_PAGES[key], None)), "filtering")
        left = [key for key in would_leave(self.in_dock()) if self.open_smart(key)]
        if left:
            self._open_first(below)
            # after QGIS laid the tabs out
            QTimer.singleShot(0, lambda: self._bring_forward(below, agent_open, dock_front))
        return left

    def _open_first(self, below: str) -> Optional[str]:
        """``below`` open in its panel, else FILTERING in its own; the one that was, None when both are in the
        dock."""
        for key in (below, "filtering"):
            panel = self._home.get(key)
            if panel is not None:
                panel.open(key)
                return key
        return None

    def _bring_forward(self, below: str, agent_open: bool, dock_front: bool) -> None:
        if self._closing:
            return
        try:
            key = self._open_first(below)
            if key is not None:
                self.raise_panel(key)
            if agent_open and "agent" in self._home:
                self.raise_panel("agent")
            elif dock_front and not self._dock.isFloating():
                self._dock.raise_()
        except RuntimeError:  # the dock went away
            pass

    def _split(self, key: str, remember: bool, place: Any) -> bool:
        """``key`` out of the panel it shares, in a new one."""
        source = self._home.get(key)
        window = self._main_window()
        if source is None or len(source.members) < 2 or window is None:
            return False
        try:
            panel = self._new_panel(window)
            self._unhost(key)
            page = source.take(key)
            panel.add(key, page, key in BOTTOM)
            self._home[key] = panel
            panel.retitle()
            self._unpin(key, panel)
            self._settle_panel(source)
            self._after_change()
            self._place(panel, window, place)
            if remember:
                self._remember()
            return True
        except RuntimeError:
            return False
        except Exception:
            logger.exception("Section %s could not be given its own panel", key)
            self._bring_home(key)
            return False

    def attach(self, key: str, remember: bool = True) -> bool:
        """``key`` back in the dock, folded; its panel goes with its last section."""
        panel = self._home.get(key)
        if panel is None:
            return False
        try:
            try:
                self._unhost(key)
            except RuntimeError:
                raise
            except Exception:  # its page still has to leave: left there, it would go with the panel
                logger.exception("The buttons of %s could not leave its panel", key)
            page = panel.take(key)
            if page is not None:
                self._into_dock(key, page)
        except RuntimeError:
            logger.debug("Section %s not brought back: the dock went away", key, exc_info=True)
        except Exception:
            logger.exception("Section %s could not be brought back to the dock", key)
        self._home.pop(key, None)
        self._rescue(key, panel)
        try:
            if key in panel.members:  # its page did not leave the usual way: the panel does not list it any more
                panel.take(key)
        except RuntimeError:
            pass
        try:
            self._settle_panel(panel)
        except RuntimeError:  # the panel went away: the other sections still have to come back (attach_all)
            logger.debug("The panel of %s was gone when it was settled", key, exc_info=True)
        try:
            self._after_change()
        except RuntimeError:
            pass
        except Exception:  # the plugin unloads, its controllers are gone: the other panels still have to go
            logger.debug("The dock was not refreshed after %s came back", key, exc_info=True)
        if remember:
            self._remember()
        return True

    def attach_all(self, remember: bool = True) -> None:
        """Every section back in the dock. Remembered: none is kept as apart, not even one that is turned off
        now (it used to go back to its panel the day it was turned on again, against this last word)."""
        for key in self.detached():
            self.attach(key, remember)
        if remember:
            _save(())

    def shutdown(self) -> None:
        """The plugin unloads: the sections go back to the dock and their panels go, what was apart stays saved."""
        self._closing = True
        self.attach_all(remember=False)

    def restore(self) -> List[str]:
        """The panels of the last time, with their sections in their order: those that are in the dock by now
        (AGENT comes after the others). Called when the dock is built, and again when AGENT is installed. The
        places and sizes QGIS kept are taken as they are: nothing is resized here (``resize_soon``)."""
        restored: List[str] = []
        try:
            if self._dock.parentWidget() is None:
                return restored  # the dock is not in the window of QGIS yet: its panels are placed after it
        except RuntimeError:
            return restored
        self._restoring = True
        try:
            return self._restore(restored)
        finally:
            self._restoring = False

    def _restore(self, restored: List[str]) -> List[str]:
        for group in _saved():
            panel = next((self._home[key] for key in group if key in self._home), None)
            came = False
            for position, key in enumerate(group):
                if key in self._home:
                    continue
                if panel is None:
                    # Under the name of the first section of the group, there or not yet: where QGIS kept it.
                    done = self.detach(key, remember=False, named=group[0])
                else:  # at its place among those that are there, behind the tab the panel may share
                    index = sum(1 for mate in group[:position] if mate in panel.members)
                    done = self.move(key, panel, index=index, remember=False, front=False)
                if done:
                    restored.append(key)
                    panel = self._home[key]
                    came = True
            try:
                if came and panel is not None and panel.members:
                    panel.open(panel.members[0])  # not the last one that came
            except RuntimeError:
                pass
        self._fuse_tabbed()  # panels QGIS put back as tabs of each other (an older arrangement) merge
        return restored

    # --- the pages, out of the dock and back -----------------------------------------

    def _out_of_dock(self, key: str) -> Any:
        """The page of ``key``, out of its stack; its chip leaves the rail of the dock."""
        from .section_bars import SECTION_PAGES
        sections = self._sections()
        if key in BOTTOM:
            area = self._page_area(key)
            if area is None or sections is None:
                return None
            toolbox = self._dock.toolBox_tabTools
            page = getattr(self._dock, SECTION_PAGES[key])
            if toolbox.currentWidget() is page:  # before its item is turned off: QToolBox would open the next one
                toolbox.setCurrentWidget(sections._nothing)
            toolbox.setItemEnabled(toolbox.indexOf(page), False)
            self._origins[key] = area
            area.takeWidget()
            sections.detached.add(key)
            return page
        page = sections._pages.get(key) if sections is not None else None
        if page is None:
            return None
        was_open = sections.is_open(key)
        sections._top_layout.removeWidget(page)
        sections.detached.add(key)
        if was_open and "exploring" not in sections.detached:
            sections.open_top("exploring")  # in its own panel, EXPLORING stays where the user put it
        return page

    def _into_dock(self, key: str, page: Any) -> None:
        from .section_bars import SECTION_PAGES
        sections = self._sections()
        if sections is not None:
            sections.detached.discard(key)
        if key in BOTTOM:
            area = self._origins.pop(key, None)
            toolbox = self._dock.toolBox_tabTools
            if area is None:  # never left in a panel that goes: it waits in the tool box, hidden
                page.setParent(toolbox)
                page.hide()
                return
            area.setWidget(page)
            page.show()
            toolbox.setItemEnabled(toolbox.indexOf(getattr(self._dock, SECTION_PAGES[key])), True)
            return
        if sections is None:
            return
        sections.place_top(key)  # under the rail, or under its header when the headers are stacked

    def _unhost(self, key: str) -> None:
        """The bar of the buttons of ``key`` leaves its panel before its page does (it would go with its column)."""
        bars = self._bars()
        if bars is not None:
            bars.host(key, None)

    def _rescue(self, key: str, panel: Any) -> None:
        """Nothing of the dock stays in a panel that goes away: left there, it would be deleted with it. What the
        way back did not take (it failed half way) waits hidden in the dock."""
        try:
            from qgis.PyQt.QtWidgets import QScrollArea
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
                viewport = widget.parentWidget()
                area = viewport.parentWidget() if viewport is not None else None
                if isinstance(area, QScrollArea) and area.widget() is widget:
                    area.takeWidget()
                widget.setParent(home)
                widget.hide()
        except RuntimeError:  # the dock went away
            pass
        except Exception:
            logger.exception("The panel of %s could not be emptied", key)

    # --- the panels ---------------------------------------------------------------

    def _new_panel(self, window: Any) -> Any:
        from qgis.PyQt.QtCore import Qt
        dock = self._dock
        panel = self._panel_class(window, self.can_take, self._dark)
        contents = getattr(dock, CONTENTS_NAME, None)
        if contents is not None:  # the background of the dock is painted from its style sheet, or not at all
            styled = Qt.WidgetAttribute.WA_StyledBackground
            panel.widget().setAttribute(styled, contents.testAttribute(styled))
        self._style(panel)
        panel.closed_by_user.connect(self._on_panel_closed)
        panel.section_dropped.connect(lambda key, target: self.move(key, target))
        panel.rail.reordered.connect(lambda order, target=panel: self._on_reordered(target, order))
        panel.rail.dropped_in.connect(lambda key, index, target=panel: self.move(key, target, index))
        panel.rail.dropped_out.connect(self._on_dropped_out)
        panel.rail.menu_requested.connect(lambda key, place, target=panel: self._popup(key, target, place))
        # Dropped as a tab of another FilterMate panel, or of the dock (visibilityChanged: see the dock above).
        for signal in ("topLevelChanged", "dockLocationChanged", "visibilityChanged"):
            getattr(panel, signal).connect(lambda *_args, mover=panel: self._moved(mover))
        for signal in ("topLevelChanged", "dockLocationChanged"):  # floated, docked, put in another area
            getattr(panel, signal).connect(lambda *_args: self._resize_soon(late=True))
        panel.rail.chosen.connect(lambda _key: self._resize_soon())  # another of its sections opened
        panel.installEventFilter(self._watch)  # dropped with the mouse within its area: no signal says so
        # Its tab selected: Qt shows nothing again (the page behind a tab was never hidden), so the page is told.
        panel.visibilityChanged.connect(lambda visible, host=panel: self._on_panel_visible(host, visible))
        shortcuts = getattr(dock, "keyboard_shortcuts_for", None)
        if callable(shortcuts):  # F5, Ctrl+Z and Ctrl+Y of the dock, with the focus in the panel
            panel.shortcuts = shortcuts(panel)
        panel.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)  # group, merge: on its title
        panel.customContextMenuRequested.connect(lambda pos, host=panel: self._show_panel_menu(host, pos))
        rails = getattr(dock, "_fm_rails", None)
        if isinstance(rails, list):
            rails.append(panel.rail)  # its icons follow the theme, as those of the rails of the dock
        self._panels.append(panel)
        return panel

    def _dark(self) -> bool:
        return bool(getattr(getattr(self._dock, "_icon_manager", None), "is_dark_mode", False))

    def _settle_panel(self, panel: Any) -> None:
        """After a section left ``panel``: it goes with its last one, else it is named after those left."""
        if panel.members:
            panel.retitle()
        else:
            self._forget(panel)

    def _forget(self, panel: Any) -> None:
        if panel in self._panels:
            self._panels.remove(panel)
        rails = getattr(self._dock, "_fm_rails", None)
        if isinstance(rails, list) and panel.rail in rails:
            rails.remove(panel.rail)
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

    def _place(self, panel: Any, window: Any, place: Any = None) -> None:
        """Where QGIS remembers the panel; else below the dock when the dock can spare the height, beside it
        otherwise. ``place``: floating there (a chip dropped out of every panel). Never as a tab of the dock or of
        another panel of FilterMate: they would merge."""
        from qgis.PyQt.QtCore import QPoint, Qt
        # restoreDockWidget before any addDockWidget, which forgets the place QGIS kept. So not iface.addDockWidget:
        # the panel is listed in the menu of the panels by hand.
        _list_panel(window, panel)
        dock = self._dock
        area = window.dockWidgetArea(dock)
        docked = area != Qt.DockWidgetArea.NoDockWidgetArea and not dock.isFloating()
        target = area if docked else Qt.DockWidgetArea.RightDockWidgetArea
        if place is not None:
            window.addDockWidget(target, panel)
            self._float(panel, place - QPoint(max(FLOATING_SIZE[0], dock.width()) // 2, 12), place)
            panel.show()
        elif window.restoreDockWidget(panel):
            panel.show()
            if self._tabbed_with_ours(panel, window):
                # The place QGIS kept is a tab of the dock or of another panel (it merged there once): a new one.
                self._place_new(panel, window, target, docked)
        else:
            self._place_new(panel, window, target, docked)
        if self._hidden_with_dock:
            panel.hide()  # the dock is closed: its panels come back with it
            self._offer(panel, False)

    def _place_new(self, panel: Any, window: Any, target: Any, docked: bool) -> None:
        """A first place for ``panel``: below the dock or beside it, above it with EXPLORING (what it selects
        stays over FILTERING, which works on it); where that makes it a tab of the dock (the dock shares its tabs
        with other panels of QGIS, and a panel split from a tab is one more tab), at the end of the area, then
        across it, then floating beside the dock."""
        from qgis.PyQt.QtCore import QPoint, Qt
        dock = self._dock
        window.addDockWidget(target, panel)
        manual = not self._auto()  # else EXPLORING gets what the next pass (resize_soon) leaves it
        if docked and not window.tabifiedDockWidgets(dock):
            room = dock.height()
            wanted = 0 if STAYS in panel.members else self._height_below(panel)
            if STAYS in panel.members:
                # Qt splits the room of the first of the two and moves the second one into it. The panel first
                # takes its place in the room of the dock, under it; then the dock comes under the panel. (The
                # panel left at the end of the area, the dock went down there with it, below the panels of QGIS
                # that were under it.)
                share = max(PANEL_MIN_HEIGHT, int(room * EXPLORING_SHARE))
                window.splitDockWidget(dock, panel, Qt.Orientation.Vertical)
                window.splitDockWidget(panel, dock, Qt.Orientation.Vertical)
                if manual and room - share >= PANEL_MIN_HEIGHT:
                    window.resizeDocks([panel, dock], [share, room - share], Qt.Orientation.Vertical)
            elif wanted:  # the room of the dock shared: the section at its own height, the dock keeps the larger part
                # (In auto too: an elastic panel, AGENT, keeps this share afterwards, rather than half of the room.)
                window.splitDockWidget(dock, panel, Qt.Orientation.Vertical)
                height = min(wanted, max(PANEL_MIN_HEIGHT, room - self._minimum(dock)))  # wanted alone in manual
                window.resizeDocks([dock, panel], [room - height, height], Qt.Orientation.Vertical)
            else:
                window.splitDockWidget(dock, panel, Qt.Orientation.Horizontal)
        if self._restoring:
            self._resize_soon(panel)  # a panel QGIS kept no place for: its column, not those QGIS restored
        panel.show()
        if not self._tabbed_with_ours(panel, window):
            return
        window.addDockWidget(target, panel)
        if not self._tabbed_with_ours(panel, window):
            return
        upright = target in (Qt.DockWidgetArea.LeftDockWidgetArea, Qt.DockWidgetArea.RightDockWidgetArea)
        window.addDockWidget(target, panel, Qt.Orientation.Horizontal if upright else Qt.Orientation.Vertical)
        if not self._tabbed_with_ours(panel, window):
            return
        corner = dock.mapToGlobal(QPoint(0, 0))
        self._float(panel, corner - QPoint(max(FLOATING_SIZE[0], dock.width()) + 12, 0), corner)

    def _float(self, panel: Any, corner: Any, place: Any) -> None:
        """``panel`` floating with its corner at ``corner``, whole on the screen that holds ``place``."""
        panel.setFloating(True)
        panel.resize(max(FLOATING_SIZE[0], self._dock.width()), FLOATING_SIZE[1])
        panel.move(self._on_screen(corner, panel.width(), panel.height(), place))

    def _tabbed_with_ours(self, panel: Any, window: Any) -> bool:
        """``panel`` is a tab of the dock or of another panel of FilterMate: they would merge at once."""
        try:
            layout = window.layout()
            if layout is not None:
                layout.activate()  # the tabs are read from the layout once it is applied, not from what was asked
            mates = window.tabifiedDockWidgets(panel)
        except (RuntimeError, AttributeError):
            return False
        return any(mate is self._dock or mate in self._panels for mate in mates)

    @staticmethod
    def _on_screen(corner: Any, width: int, height: int, place: Any) -> Any:
        """``corner`` brought back so that a window of this size is whole on the screen that holds ``place``."""
        try:
            from qgis.PyQt.QtCore import QPoint
            from qgis.PyQt.QtGui import QGuiApplication
            screen = QGuiApplication.screenAt(place) or QGuiApplication.primaryScreen()
            if screen is None:
                return corner
            area = screen.availableGeometry()
            return QPoint(*floating_corner((corner.x(), corner.y()), (width, height),
                                           (area.left(), area.top(), area.right(), area.bottom())))
        except Exception:
            return corner

    def _height_below(self, panel: Any) -> int:
        """The height ``panel`` gets below the dock, 0 when the dock cannot spare it (``panel_height``)."""
        dock = self._dock
        contents = dock.widget()
        if contents is not None and contents.layout() is not None:
            contents.layout().activate()  # the minimum of the dock without the section that just left it
        room = dock.height()
        spare = room - self._minimum(dock)
        window = self._main_window()
        if self._auto() and window is not None:
            # The pass that follows shares the whole column: what every dock of it has above its minimum (EXPLORING
            # above the dock held to FILTERING) can go to the panel. The dock alone put it beside the dock.
            column = self._column(window, dock) or [dock]
            room = sum(other.height() for other in column)
            spare = sum(other.height() - self._minimum(other) for other in column)
        return panel_height(panel.widget().sizeHint().height() + TITLE_ROOM, room, spare)

    def relax_dock(self, profile_applied: bool = False) -> None:
        """With EXPLORING, FILTERING, EXPORTING or CONFIGURATION in a panel, the dock needs less height than its
        display profile asks for all of them (600 px in the normal one): no minimum of its own, Qt then holds it
        to what its contents need. The profile's minimum comes back with the last of them. ``profile_applied``:
        the dimensions of a profile were just applied, the minimum of the dock is the one to give back."""
        try:
            dock = self._dock
            apart = any(key != "agent" for key in self._home)  # AGENT alone apart leaves the dock as tall as ever
            if profile_applied or (apart and self._dock_minimum is None):
                # Read once per profile: afterwards Qt writes what the contents need, and a minimum read again
                # after sections went, came back and went again was no longer the one of the profile. Not a
                # minimum of 0: it is the one given up while sections are apart, when the profile set none.
                if dock.minimumHeight() > 0:
                    self._dock_minimum = dock.minimumHeight()
            if apart:
                if dock.minimumHeight() > 0:
                    dock.setMinimumHeight(0)
                self._dock_relaxed = True
            elif self._dock_relaxed:
                self._dock_relaxed = False
                if self._dock_minimum is not None:
                    dock.setMinimumHeight(self._dock_minimum)
        except RuntimeError:  # the dock went away
            pass

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
        for panel in self._panels:
            try:
                found.extend(panel.findChildren(*args, **kwargs))
            except RuntimeError:  # a panel that is going away
                pass
        return found

    # --- the heights: each panel at the height of what it shows ----------------------------------------------------

    def _auto(self) -> bool:
        return panel_sizing(getattr(self._dock, "CONFIG_DATA", None)) == PANEL_SIZING_AUTO

    def resize_soon(self) -> None:
        """The dock and the panels sized again, once the layout of what changed is applied: a setting changed what
        they show (a section turned on or off, the height of the rows, the place of the buttons)."""
        self._resize_soon()

    def _resize_soon(self, only: Any = None, late: bool = False) -> None:
        """A pass of ``_resize_now`` on the next turn of the loop of Qt, after the layout of what changed: one for
        any number of changes. ``only``: that panel and its column, else every one. ``late``: once a panel dropped
        with the mouse is plugged (``FUSION_SETTLE_MS``). Not while the panels of the last time are restored: QGIS
        gives them the places and sizes it kept (but a panel it kept none for is placed, and sized)."""
        if self._closing or (only is None and self._restoring):
            return
        from qgis.PyQt.QtCore import QTimer
        if late:
            QTimer.singleShot(FUSION_SETTLE_MS, lambda: self._resize_soon(only))
            return
        if only is None:
            self._resize_all = True
        elif only not in self._resize_only:
            self._resize_only.append(only)
        if not self._resize_pending:
            self._resize_pending = True
            QTimer.singleShot(0, self._resize_now)

    def _resize_now(self) -> None:
        """Each column of the window that holds the dock or a panel of FilterMate shared again (``column_heights``):
        a rigid one (FILTERING or EXPORTING open, their rows at their own height) at the height it needs, the rest to
        the elastic ones of FilterMate, else to the other panels of QGIS. A floating one at its own height
        (``floating_height``). Nothing with ``APP.DOCKWIDGET.PANEL_SIZING`` = ``manual``."""
        self._resize_pending = False
        everything, only = self._resize_all, self._resize_only
        self._resize_all, self._resize_only = False, []
        if self._closing or not self._auto():
            return
        if self._drag_running():  # a chip is being dragged: the panels may change once it is dropped
            if everything:
                self._resize_soon(late=True)
            for panel in only:
                self._resize_soon(panel, late=True)
            return
        window = self._main_window()
        if window is None:
            return
        try:
            self._settle_layouts(window)
            holders = self._containers()
            targets = holders if everything else [holder for holder in only if holder in holders]
            done: List[Any] = []
            seen: Dict[Any, str] = {}
            for holder in targets:
                if holder.isFloating():
                    self._size_floating(holder, seen)
                    continue
                column = self._column(window, holder)
                if column and not any(column == other for other in done):
                    done.append(column)
                    self._size_column(window, column, seen)
            for holder, kind in seen.items():
                if kind == ELASTIC:
                    self._elastic.add(holder)
                else:
                    self._elastic.discard(holder)
            self._elastic = {holder for holder in self._elastic if holder is self._dock or holder in self._panels}
        except RuntimeError:  # the dock or a panel went away
            pass
        except Exception:
            logger.exception("The panels of FilterMate could not be sized")

    @staticmethod
    def _settle_layouts(window: Any) -> None:
        """What is asked of the layouts applied now: the heights are read from them."""
        from qgis.PyQt.QtCore import QCoreApplication, QEvent
        request = int(getattr(QEvent.Type.LayoutRequest, "value", QEvent.Type.LayoutRequest))
        for _round in range(3):  # a layout applied asks its parent's again
            QCoreApplication.sendPostedEvents(None, request)
            layout = window.layout()
            if layout is not None:
                layout.activate()

    def _containers(self) -> List[Any]:
        """The dock and the panels that hold sections, those on screen (or behind a tab: Qt calls them visible)."""
        holders = [self._dock] + [panel for panel in self._panels if panel.members]
        return [holder for holder in holders if holder.isVisible()]

    def _area_docks(self, window: Any, area: Any) -> List[Any]:
        """The docks of QGIS in ``area`` of the window, on screen or behind a tab."""
        from qgis.PyQt.QtWidgets import QDockWidget
        docks = []
        # Not FindDirectChildrenOnly: given that way, PyQt found no dock at all (QGIS stable, 19 November 2026).
        for dock in window.findChildren(QDockWidget):
            try:
                if dock.parentWidget() is window and dock.isVisible() and not dock.isFloating() and dock.height() > 0 \
                        and window.dockWidgetArea(dock) == area:
                    docks.append(dock)
            except RuntimeError:  # a dock going away
                continue
        return docks

    def _column(self, window: Any, holder: Any) -> List[Any]:
        """The docks stacked with ``holder`` in its area, top to bottom (``column_of``); one for a group of tabs."""
        docks = self._area_docks(window, window.dockWidgetArea(holder))
        if holder not in docks:
            return []
        rects = [(dock.x(), dock.y(), dock.width(), dock.height()) for dock in docks]
        return [docks[index] for index in column_of(docks.index(holder), rects)]

    @staticmethod
    def _tab_mates(window: Any, dock: Any) -> List[Any]:
        """The docks ``dock`` shares its tabs with, on screen or not (Qt 5 keeps hidden docks in a group of tabs)."""
        return [mate for mate in window.tabifiedDockWidgets(dock) if mate.isVisible()]

    def _tab_room(self, window: Any, dock: Any) -> int:
        """The height of the bar of the tabs ``dock`` shares, 0 without one: Qt sizes the group with it."""
        if not self._tab_mates(window, dock):
            return 0
        from qgis.PyQt.QtWidgets import QTabBar
        rect = dock.geometry()
        for bar in window.findChildren(QTabBar):
            area = bar.geometry()
            if bar.parentWidget() is window and bar.isVisible() and min(area.right(), rect.right()) - max(area.left(), rect.left()) > 0 \
                    and (abs(area.top() - rect.bottom()) <= 12 or abs(area.bottom() - rect.top()) <= 12):
                return area.height()
        return 0

    def _size_column(self, window: Any, column: List[Any], seen: Dict[Any, str]) -> None:
        """``column`` shared again (``column_heights``). A group of tabs is a panel of QGIS, even with a panel of
        FilterMate in front: its height is that of the other tabs too. Docks side by side are one row of the
        column: elastic when one of them is, rigid at the need of the tallest one otherwise (the others keep room
        under their rows: they cannot be shorter than the row), a panel of QGIS when one is."""
        from qgis.PyQt.QtCore import Qt
        area = self._area_docks(window, window.dockWidgetArea(column[0]))
        docks, slots = [], []
        for dock in column:
            tab = self._tab_room(window, dock)
            slot = dock.height() + tab
            # The docks beside it share its height: one row of the column, sized for all of them.
            # (Same top and height, another left: a tab of its group has the same place, a dock across several rows
            # another height.)
            row = [dock] + [other for other in area if other not in column and abs(other.y() - dock.y()) <= 2
                            and abs(other.height() - dock.height()) <= 2 and abs(other.x() - dock.x()) > 2]
            kinds = []
            for one in row:
                if (one is dock and tab) or not (one is self._dock or one in self._panels) or self._tab_room(window, one):
                    kinds.append((OTHER, self._minimum(one), 0))
                    continue
                kind, need, minimum = self._measure(one)
                seen[one] = kind
                kinds.append((kind, minimum, need))
            minimum = max(entry[1] for entry in kinds) + tab
            if any(entry[0] == OTHER for entry in kinds):
                docks.append((OTHER, minimum, 0, slot))
            elif any(entry[0] == ELASTIC for entry in kinds):
                docks.append((ELASTIC, minimum, 0, slot))
            else:  # rigid side by side: the row for the one that needs the most, none cut
                docks.append((RIGID, minimum, max(entry[2] for entry in kinds), slot))
            slots.append(slot)
        heights = column_heights(docks, sum(slots))
        if any(abs(height - slot) > 1 for height, slot in zip(heights, slots)):
            window.resizeDocks(column, heights, Qt.Orientation.Vertical)

    def _size_floating(self, holder: Any, seen: Dict[Any, str]) -> None:
        """A floating panel (or the dock) at the height of what it shows (``floating_height``), whole on its screen."""
        from qgis.PyQt.QtGui import QGuiApplication
        kind, need, minimum = self._measure(holder)
        seen[holder] = kind
        screen = QGuiApplication.screenAt(holder.geometry().center()) or QGuiApplication.primaryScreen()
        frame = holder.frameGeometry().height() - holder.height()  # the title bar the window manager adds
        available = screen.availableGeometry().height() - frame if screen is not None else 0
        height = floating_height(kind, minimum, need, holder.height(), holder.sizeHint().height(),
                                 holder not in self._elastic, available)
        if abs(height - holder.height()) > 1:
            holder.resize(holder.width(), height)
            corner = self._on_screen(holder.pos(), holder.width(), height, holder.geometry().center())
            if corner != holder.pos():
                holder.move(corner)

    @staticmethod
    def _minimum(dock: Any) -> int:
        return max(dock.minimumHeight(), dock.minimumSizeHint().height())

    def _measure(self, holder: Any) -> Tuple[str, int, int]:
        """``(kind, need, minimum)`` of the dock or of a panel. Rigid with FILTERING or EXPORTING open and nothing
        else, their rows at their own height (``APP.DOCKWIDGET.SECTION_HEIGHT`` = ``fit``): it needs its height but
        the room left under the rows, in the scroll area that holds them (more when they are cut and scroll).
        Elastic otherwise: EXPLORING, AGENT and CONFIGURATION use any height, and so do the rows spread (``fill``)."""
        minimum = self._minimum(holder)
        page = self._rigid_page(holder)
        if page is None:
            return ELASTIC, 0, minimum
        return RIGID, holder.height() - self._room_under(page), minimum

    def _rigid_page(self, holder: Any) -> Any:
        """The page of FILTERING or EXPORTING, when it is all ``holder`` opens; None otherwise."""
        from .mockup_layout import ROW_SECTIONS, SECTION_FILL
        if self._dock.property("fm_section_height") == SECTION_FILL:
            return None
        if holder is self._dock:
            sections = self._sections()
            if sections is None or any(sections._open_in_stack(key) for key in sections._pages):
                return None  # AGENT or EXPLORING open above
            key = sections.bottom_key()
            if key in self._home:
                return None
        else:
            key = holder.current()
        page = self._page(key) if key in ROW_SECTIONS else None
        return page if page is not None and page.isVisible() else None

    @staticmethod
    def _room_under(page: Any) -> int:
        """The height left empty under ``page`` in the scroll area that holds it (the tool box, or the column of a
        panel); less than 0 when the page is cut and scrolls."""
        from qgis.PyQt.QtWidgets import QScrollArea
        viewport = page.parentWidget()
        area = viewport.parentWidget() if viewport is not None else None
        if not isinstance(area, QScrollArea) or area.widget() is not page:
            return 0
        return viewport.height() - page.sizeHint().height()

    def _signature(self) -> Any:
        """Where the dock and the panels are: floating, or in which area and column, with which tabs. The same
        after a tab is selected or a separator dragged; another after a panel is dropped elsewhere."""
        window = self._main_window()
        if window is None:
            return None
        rows = []
        for holder in self._containers():
            if holder.isFloating():
                rows.append((holder.objectName(), "floating"))
                continue
            column = self._column(window, holder)
            mates = sorted(mate.objectName() for mate in self._tab_mates(window, holder))
            rows.append((holder.objectName(), _area_number(window.dockWidgetArea(holder)),
                         tuple(dock.objectName() for dock in column), tuple(mates)))
        return tuple(rows)

    def _on_mouse(self, pressed: bool) -> None:
        """A dock dropped with the mouse within its area (as a tab, or above another one) says nothing: where the
        panels are is compared from the press to the end of the drop. A click, or a separator dragged, changes
        nothing of it: the sizes the user set stay."""
        if not self._auto():
            return
        if pressed:
            try:
                self._press_signature = self._signature()
            except Exception:  # never in the way of a click (a dock going away raises RuntimeError)
                self._press_signature = None
            return
        before, self._press_signature = self._press_signature, None
        if before is None:
            return
        from qgis.PyQt.QtCore import QTimer

        def compare() -> None:
            try:
                if not self._closing and self._signature() != before:
                    self._resize_soon()
            except Exception:  # the dock went away (RuntimeError): nothing to size
                logger.debug("The panels were not compared after a drop", exc_info=True)
        QTimer.singleShot(FUSION_SETTLE_MS, compare)  # once the drop is plugged

    def _on_dock_opened(self) -> None:
        """The user opened another section in the dock: with sections apart, what it needs may have changed (the
        dock in one piece is left as the user sized it)."""
        if self._home:
            self._resize_soon()

    # --- merged when put together ---------------------------------------------------

    def _moved(self, mover: Any) -> None:
        """A panel, or the dock, was dropped somewhere: as a tab of another one of FilterMate, they merge. Looked
        at once the drop is over, and again once Qt has plugged it: dropped with the mouse, a dock is a tab only
        when the animation of its drop ends (QGIS LTR, 17 November 2026), after the signal."""
        if self._closing or self._fusion_pending:
            return
        self._fusion_pending = True
        from qgis.PyQt.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._fuse_tabbed(mover))
        QTimer.singleShot(FUSION_SETTLE_MS, lambda: self._fuse_tabbed(mover, late=True))

    def _fuse_tabbed(self, mover: Any = None, late: bool = False) -> bool:
        """Merge the panels of FilterMate that are tabs of each other, or of the dock (``fusion``). True when some
        were. ``late``: the second look, once the drop is plugged (the first one let other moves be looked at)."""
        if not late:
            self._fusion_pending = False
        if self._closing or self._fusing:
            return False
        if self._drag_running():
            # A chip is being dragged, and the loop of its drag runs this timer: a merge now could delete the
            # panel whose rail started the drag, under it. Looked at again once the drag is over.
            from qgis.PyQt.QtCore import QTimer
            QTimer.singleShot(FUSION_SETTLE_MS, lambda: self._fuse_tabbed(mover, late=True))
            return False
        window = self._main_window()
        if window is None:
            return False
        self._fusing = True
        merged = False
        try:
            for _round in range(2 * len(DETACHABLE)):
                order = list(self._panels)
                tabbed = [[mate for mate in window.tabifiedDockWidgets(panel)] for panel in order]
                with_dock = [panel for panel, mates in zip(order, tabbed) if self._dock in mates]
                step = fusion(order, tabbed, with_dock, mover)
                if step is None:
                    break
                source, target = step
                for key in list(source.members):
                    if target is None:
                        self.attach(key, remember=False)
                    else:
                        self.move(key, target, remember=False)
                if source in self._panels:  # a section that could not move: stop, rather than turn in circles
                    break
                merged = True
        except RuntimeError:  # the dock or a panel went away
            pass
        finally:
            self._fusing = False
        if merged:
            self._remember()
        return merged

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
                for key, panel in self._home.items():
                    bars.host(key, panel.box_layout(key))
                bars.settle()
        select = getattr(dock, "select_tabTools_index", None)
        if callable(select) and not self._closing:  # not while the plugin unloads: its controllers are gone
            select()  # the buttons of a section apart act whatever is open in the dock
        self.relax_dock()
        sections = self._sections()
        if sections is not None:
            sections.refresh_rails()  # the chip of a section apart leaves its rail; with none left below, the
            # upper stack takes the dock
        self._resize_soon()  # the dock and the panels at the height of what they show now

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
        _save(remembered(self.groups(), _saved(), self._present()))

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
        """The panel of ``key`` in view, with ``key`` open in it."""
        panel = self._home.get(key)
        if panel is None:
            return
        try:
            panel.open(key)
            if self._hidden_with_dock:
                return  # the dock is closed: its panels come back with it, this one with ``key`` open
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

    def _on_event(self, watched: Any, event: Any) -> bool:
        """True when the event was taken here (the chip of a section apart dragged over the dock)."""
        from qgis.PyQt.QtCore import QEvent
        try:
            kind = event.type()
            presses = (QEvent.Type.MouseButtonPress, QEvent.Type.NonClientAreaMouseButtonPress)
            if kind in presses or kind in (QEvent.Type.MouseButtonRelease, QEvent.Type.NonClientAreaMouseButtonRelease):
                if watched is self._dock or watched in self._panels:  # its title: a drag of the dock may start
                    self._on_mouse(kind in presses)
                return False
            if watched is getattr(self._dock, CONTENTS_NAME, None):
                if kind == QEvent.Type.StyleChange:
                    for panel in self._panels:
                        self._style(panel)
            elif watched is not self._dock:
                return False
            elif kind == QEvent.Type.Close:
                self._on_dock_closed()  # the close event itself: the dock may not say that it closes
            elif kind == QEvent.Type.Show and self._hidden_with_dock:
                self._hidden_with_dock = False
                for panel in self._panels:
                    self._offer(panel, True)
                    panel.show()
            elif kind in (QEvent.Type.DragEnter, QEvent.Type.DragMove, QEvent.Type.Drop):
                key = self._dragged_section(event)
                if key is None or key not in self._home:
                    return False
                event.acceptProposedAction()
                if kind == QEvent.Type.Drop:
                    self.attach(key)
                return True
        except RuntimeError:
            pass
        return False

    @staticmethod
    def _dragged_section(event: Any) -> Optional[str]:
        from ..widgets.section_rail import SECTION_MIME
        mime = event.mimeData()
        if mime is None or not mime.hasFormat(SECTION_MIME):
            return None
        return bytes(mime.data(SECTION_MIME)).decode("utf-8")

    def _on_dock_closed(self) -> None:
        """The dock is closed: the panels of its sections go with it, and come back when it is shown again. They
        are hidden, not closed: a panel the user closes brings its sections back. A panel made while the dock is
        closed (a section turned on again) waits for it too. Their entries of View > Panels are off meanwhile: a
        panel shown with the dock closed would work on a dock whose layer chooser was emptied, whose agent stopped
        and whose map tools were given back (closeEvent); the classic dock could not be used in that state."""
        self._hidden_with_dock = True
        for panel in self._panels:
            try:
                panel.hide()
            except RuntimeError:
                continue
            self._offer(panel, False)

    @staticmethod
    def _offer(panel: Any, offered: bool) -> None:
        """The entry of ``panel`` in View > Panels can be used (the dock is open) or not."""
        try:
            panel.toggleViewAction().setEnabled(offered)
        except RuntimeError:  # the panel went away
            pass

    def _on_dock_destroyed(self, *_args: Any) -> None:
        """The dock went without the plugin unloading it: its panels would stay in QGIS with nothing behind them."""
        self._closing = True
        panels, self._panels, self._home = list(self._panels), [], {}
        for panel in panels:
            self._forget(panel)

    def _on_panel_closed(self, panel: Any) -> None:
        if self._closing or panel not in self._panels:
            return
        from qgis.PyQt.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._attach_closed(panel))  # after the close event of the panel is over

    def _attach_closed(self, panel: Any) -> None:
        """The user closed ``panel``: its sections come back. Not when QGIS itself is closing (a floating panel is
        closed with its windows): they stay apart for the next time."""
        try:
            window = self._main_window()
            if self._closing or window is None or not window.isVisible() or panel not in self._panels:
                return
            members = list(panel.members)
        except RuntimeError:
            return
        for key in members:
            self.attach(key)

    def _on_panel_visible(self, panel: Any, visible: bool) -> None:
        """``panel`` comes in view (shown, or its tab selected): the page of its open section, when it tells that
        it is shown (AGENT: an offer waiting in its thread is seen then), says so, once Qt has laid the tabs out."""
        if not visible or panel not in self._panels or self._closing:
            return
        from qgis.PyQt.QtCore import QTimer

        def tell() -> None:
            try:
                key = panel.current() if panel in self._panels else None
                sections = self._sections()
                shown = getattr(panel.page(key), "shown", None) if key is not None else None
                if shown is not None and hasattr(shown, "emit") and sections is not None and sections.is_open(key):
                    shown.emit()
            except (RuntimeError, TypeError):  # the page went away
                pass
        QTimer.singleShot(0, tell)

    def _drag_running(self) -> bool:
        """The chip of a section is being dragged, from a rail of the dock or of a panel."""
        rails = getattr(self._dock, "_fm_rails", None)
        return any(bool(getattr(rail, "_dragging", False)) for rail in rails) if isinstance(rails, list) else False

    def _on_bottom_changed(self, index: int) -> None:
        """Something opened a section that is apart (a script, the agent): its panel comes forward instead."""
        from .section_bars import SECTION_PAGES
        try:
            page = self._dock.toolBox_tabTools.widget(index)
            for key in BOTTOM:
                if key in self._home and page is getattr(self._dock, SECTION_PAGES[key], None):
                    sections = self._sections()
                    self._dock.toolBox_tabTools.setCurrentWidget(sections._nothing)
                    self.raise_panel(key)
                    opener = getattr(sections, "_open_alone", None)
                    if callable(opener):
                        opener()  # what was open in the dock was folded for it: the dock keeps one section open
                    return
        except (RuntimeError, AttributeError):
            pass

    def _on_reordered(self, panel: Any, order: Sequence[str]) -> None:
        """The chips of a panel were dragged into another order: its sections follow, its name too (that of the
        first one), and the order is kept."""
        try:
            panel.set_order(order)
            panel.retitle()
        except RuntimeError:
            return
        self._remember()

    def _on_dropped_out(self, key: str, place: Any) -> None:
        """A chip was dropped where no rail and no panel took it: its section gets a new panel there. Not within
        the dock or the panel it was dragged from: a drop that missed the rail changes nothing."""
        try:
            dock = self._dock
            home = self._home.get(key)
            if self._holds(home or dock, place):
                return
            target = next((panel for panel in self._panels if panel is not home and self._holds(panel, place)), None)
            if target is not None:
                self.move(key, target)  # on another panel, where nothing took the drop: it joins it all the same
                return
            if home is not None and self._holds(dock, place):
                self.attach(key)  # on the dock: it comes back
                return
            if home is not None and len(home.members) < 2:
                return  # alone in its panel already
        except RuntimeError:
            return
        self.detach(key, place=place)

    @staticmethod
    def _holds(widget: Any, place: Any) -> bool:
        """``place`` of the screen is on ``widget``, where it shows: behind the tab of another panel it shows
        nowhere, though Qt calls it visible. (Not its visible region: Qt takes its opaque children out of it.)"""
        from qgis.PyQt.QtWidgets import QApplication
        if not widget.isVisible():
            return False
        at = QApplication.widgetAt(place)
        return at is not None and (at is widget or widget.isAncestorOf(at))

    # --- the menu of a section --------------------------------------------------------

    def _on_chip_menu(self, key: str, place: Any) -> None:
        """A right click on the chip of a section, in a rail of the dock."""
        self._popup(key, self._dock, place)

    def build_menu(self, key: str, parent: Any) -> Any:
        """The menu of the section ``key`` (on its chip, on the title of its panel): separate, group, merge. None
        when it would be empty."""
        from qgis.PyQt.QtWidgets import QMenu
        entries = [(command, name) for command, name in menu_entries(key, self.groups(), self._present())
                   if command not in ("detach", "group") or key in self._home or self.can_detach(key)]
        if not entries:
            return None
        texts = {
            "detach": lambda name: _tr("Open {} in its own panel").format(TITLES[name]),
            "detach_all": lambda name: _tr("Take every section out of FilterMate"),
            "group": lambda name: _tr("Group with {}").format(panel_title(self._home[name].members)),
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

    def _popup(self, key: str, parent: Any, place: Any) -> None:
        """The menu of ``key`` at ``place`` of the screen; never modal: the headless checks reach this path."""
        try:
            menu = self.build_menu(key, parent)
            if menu is not None:
                menu.aboutToHide.connect(menu.deleteLater)
                menu.popup(place)
        except RuntimeError:
            pass

    def _show_panel_menu(self, panel: Any, pos: Any) -> None:
        """A right click on the title of a panel (not in its contents, which have their own menus): the menu of its
        open section."""
        try:
            holder = panel.widget()
            if (holder is not None and holder.geometry().contains(pos)) or panel.current() is None:
                return
            self._popup(panel.current(), panel, panel.mapToGlobal(pos))
        except RuntimeError:
            pass


def install_section_panels(dock: Any) -> Optional[SectionPanels]:
    """``dock._fm_panels``: its sections can go to panels. None when the dock has no sections to move."""
    if getattr(dock, "_fm_sections", None) is None:
        return None
    try:
        dock._fm_panels = SectionPanels(dock)
        return dock._fm_panels
    except Exception:
        logger.exception("The sections cannot be shown in their own panels")
        return None
