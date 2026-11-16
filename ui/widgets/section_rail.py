# -*- coding: utf-8 -*-
"""A horizontal rail that lists sections: one chip each, the open one with its name.

* It stands above the sections it lists: AGENT / EXPLORING at the top of the dock, FILTERING / EXPORTING /
  CONFIGURATION above the lower stack, and the sections a panel of QGIS holds (ui/layout/section_panels.py). It
  replaces the headers stacked one above the other: one row of 34 px whatever the number of sections.
* A click on a chip opens its section. A chip is dragged along the rail to put the sections in another order, and
  onto another rail to move its section there (the rail says which sections it takes).
* The names of the sections are never translated, as on the headers before.

The order and the moves are plain rules (``drop_index``, ``moved``, ``parse_order``); the widget is at the end.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable, List, Optional, Sequence

SECTION_MIME = "application/x-filtermate-section"
CHIP_NAME = "pushButton_rail_section"  # every chip bears this name: one rule of the style sheet for all
RAIL_NAME = "widget_section_rail"
TITLES = {"agent": "AGENT", "exploring": "EXPLORING", "filtering": "FILTERING", "exporting": "EXPORTING",
          "configuration": "CONFIGURATION"}
ICONS = {"agent": "agent", "exploring": "zoom", "filtering": "filter", "exporting": "export",
         "configuration": "settings"}
RAIL_HEIGHT = 34  # as a section header
CHIP_GAP = 6
ICON_SIZE = 16


def drop_index(centres: Sequence[float], x: float) -> int:
    """Where a chip dropped at ``x`` goes among chips whose centres are ``centres`` (left to right, the dragged
    one left out): before the first chip whose centre is right of ``x``."""
    for index, centre in enumerate(centres):
        if x < centre:
            return index
    return len(centres)


def moved(order: Sequence[str], key: str, index: int) -> List[str]:
    """``order`` with ``key`` at ``index``, counted among the others: a chip moved along its rail, or come from
    another one."""
    others = [name for name in order if name != key]
    index = max(0, min(index, len(others)))
    return others[:index] + [key] + others[index:]


def parse_order(value: Any, known: Iterable[str]) -> List[str]:
    """The order kept in the settings, for the sections ``known``: those it names first, as it names them, then
    the others in their usual order. Names it does not know, and repeats, are left out."""
    usual = list(known)
    if isinstance(value, str):
        names = [name.strip().lower() for name in value.split(",")]
    elif isinstance(value, (list, tuple)):
        names = [str(name).strip().lower() for name in value]
    else:
        names = []
    ordered: List[str] = []
    for name in names:
        if name in usual and name not in ordered:
            ordered.append(name)
    return ordered + [name for name in usual if name not in ordered]


def format_order(order: Iterable[str]) -> str:
    return ",".join(order)


def _rail_class():
    """The widget, made when Qt is there (the rules above are read without it)."""
    from qgis.PyQt.QtCore import QEvent, QMimeData, QObject, QPoint, QSize, Qt, pyqtSignal
    from qgis.PyQt.QtGui import QCursor, QDrag
    from qgis.PyQt.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

    class SectionRail(QWidget):
        chosen = pyqtSignal(str)  # a click on the chip of this section
        reordered = pyqtSignal(list)  # its chips were dragged into this order
        dropped_in = pyqtSignal(str, int)  # the chip of this section, of another rail, was dropped here at this place
        dropped_out = pyqtSignal(str, QPoint)  # its chip was dropped where nothing took it, at this place of the screen
        menu_requested = pyqtSignal(str, QPoint)  # a right click on the chip of this section, at this place of the screen

        def __init__(self, parent: Any = None, accepts: Optional[Callable[[str], bool]] = None,
                     dark: Optional[Callable[[], bool]] = None) -> None:
            super().__init__(parent)
            self.setObjectName(RAIL_NAME)
            self._accepts = accepts or (lambda _key: False)
            self._dark = dark or (lambda: False)
            self._order: List[str] = []
            self._chips: dict = {}
            self._hidden: set = set()
            self._current: Optional[str] = None
            self._press: Any = None
            self._trailer: Any = None
            self.setFixedHeight(RAIL_HEIGHT)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._row = QHBoxLayout(self)
            self._row.setContentsMargins(0, 0, 0, 0)
            self._row.setSpacing(CHIP_GAP)
            self._row.addStretch(1)
            self.setAcceptDrops(True)
            owner = self

            class _Chips(QObject):
                def eventFilter(self, watched: Any, event: Any) -> bool:  # noqa: N802 - Qt name
                    return owner._on_chip_event(watched, event)

            self._filter = _Chips(self)

        # --- what it lists ------------------------------------------------------------

        def sections(self) -> List[str]:
            return list(self._order)

        def shown_sections(self) -> List[str]:
            return [key for key in self._order if key not in self._hidden]

        def current(self) -> Optional[str]:
            return self._current

        def chip(self, key: str) -> Any:
            return self._chips.get(key)

        def set_sections(self, keys: Iterable[str]) -> None:
            """The sections listed, in this order; the chips of those that left go."""
            order = [key for key in keys if key in TITLES]
            for key in [name for name in self._chips if name not in order]:
                chip = self._chips.pop(key)
                self._row.removeWidget(chip)
                chip.setParent(None)
                chip.deleteLater()
                self._hidden.discard(key)
            for key in order:
                if key not in self._chips:
                    self._chips[key] = self._make_chip(key)
            self._order = order
            if self._current not in order:
                self._current = None
            self._lay_out()

        def set_shown(self, key: str, shown: bool) -> None:
            """Hide the chip of a section that is turned off, or shown elsewhere."""
            if shown:
                self._hidden.discard(key)
            else:
                self._hidden.add(key)
            chip = self._chips.get(key)
            if chip is not None:
                chip.setVisible(shown)

        def set_current(self, key: Optional[str]) -> None:
            """The open section: its chip is checked and shows its name; None with none open."""
            self._current = key if key in self._chips else None
            for name, chip in self._chips.items():
                chip.setChecked(name == self._current)
                chip.setText(TITLES[name] if name == self._current else "")

        def trailer(self) -> Any:
            """A muted label at the right of the rail (where the requests of AGENT go)."""
            if self._trailer is None:
                self._trailer = QLabel(self)
                self._trailer.setObjectName("label_section_rail_trailer")
                self._trailer.setTextFormat(Qt.TextFormat.PlainText)
                self._row.addWidget(self._trailer)
            return self._trailer

        def refresh_icons(self, dark: Optional[bool] = None) -> None:
            """The icons in the color of the theme (``dark`` when the caller knows it before the dock does)."""
            try:
                from ..styles.mockup_design import render_icon
            except Exception:
                return
            dark = bool(self._dark()) if dark is None else bool(dark)
            for key, chip in self._chips.items():
                icon = render_icon(ICONS[key], dark)
                if icon is not None:
                    chip.setIcon(icon)

        def move(self, key: str, index: int) -> bool:
            """The chip of ``key`` at ``index`` among the others shown; True when the order changed."""
            if key not in self._chips:
                return False
            shown = [name for name in self.shown_sections() if name != key]
            index = max(0, min(index, len(shown)))
            # Among all the sections: before the shown one it lands in front of, else after the last shown one.
            others = [name for name in self._order if name != key]
            at = others.index(shown[index]) if index < len(shown) else (
                others.index(shown[-1]) + 1 if shown else len(others))
            order = others[:at] + [key] + others[at:]
            if order == self._order:
                return False
            self._order = order
            self._lay_out()
            self.reordered.emit(list(order))
            return True

        # --- the chips ------------------------------------------------------------------

        def _make_chip(self, key: str) -> Any:
            chip = QPushButton(self)
            chip.setObjectName(CHIP_NAME)
            chip.setProperty("fm_section", key)
            chip.setCheckable(True)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            chip.setToolTip(TITLES[key])
            chip.setAccessibleName(TITLES[key])
            chip.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
            chip.setFixedHeight(RAIL_HEIGHT)
            chip.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            chip.customContextMenuRequested.connect(
                lambda pos, name=key, button=chip: self.menu_requested.emit(name, button.mapToGlobal(pos)))
            chip.clicked.connect(lambda _checked=False, name=key: self._on_clicked(name))
            chip.installEventFilter(self._filter)
            try:
                from ..styles.mockup_design import render_icon
                icon = render_icon(ICONS[key], bool(self._dark()))
                if icon is not None:
                    chip.setIcon(icon)
            except Exception:  # nosec B110 - a chip without its icon still names its section in its tooltip
                pass
            return chip

        def _lay_out(self) -> None:
            for chip in self._chips.values():
                self._row.removeWidget(chip)
            for position, key in enumerate(self._order):
                chip = self._chips[key]
                self._row.insertWidget(position, chip)
                chip.setVisible(key not in self._hidden)
            self.set_current(self._current)

        def _on_clicked(self, key: str) -> None:
            self.set_current(self._current)  # the click toggled the chip: what is open is said by the owner
            self.chosen.emit(key)

        # --- drag and drop --------------------------------------------------------------

        def _on_chip_event(self, chip: Any, event: Any) -> bool:
            kind = event.type()
            if kind == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._press = (chip, event.pos())
            elif kind == QEvent.Type.MouseButtonRelease:
                self._press = None
            elif kind == QEvent.Type.MouseMove and self._press is not None and self._press[0] is chip:
                if (event.pos() - self._press[1]).manhattanLength() >= QApplication.startDragDistance():
                    self._press = None
                    self._drag(chip)
                    return True
            return False

        def _drag(self, chip: Any) -> None:
            key = chip.property("fm_section")
            data = QMimeData()
            data.setData(SECTION_MIME, str(key).encode("utf-8"))
            drag = QDrag(self)
            drag.setMimeData(data)
            drag.setPixmap(chip.grab())
            drag.setHotSpot(QPoint(chip.width() // 2, chip.height() // 2))
            chip.setDown(False)
            run = getattr(drag, "exec", None) or drag.exec_  # PyQt5 before 5.15 only has exec_
            taken = run(Qt.DropAction.MoveAction)
            self.set_current(self._current)
            if taken == Qt.DropAction.IgnoreAction:  # no rail, no panel took it: its owner may give it a panel
                self.dropped_out.emit(str(key), QCursor.pos())

        @staticmethod
        def dragged_key(mime: Any) -> Optional[str]:
            if mime is None or not mime.hasFormat(SECTION_MIME):
                return None
            return bytes(mime.data(SECTION_MIME)).decode("utf-8")

        def takes(self, key: Optional[str], source: Any) -> bool:
            """A chip of this rail is put elsewhere on it; one of another rail comes if the owner takes it."""
            if key is None:
                return False
            return key in self._chips if source is self else bool(self._accepts(key))

        def dragEnterEvent(self, event: Any) -> None:  # noqa: N802 - Qt name
            if self.takes(self.dragged_key(event.mimeData()), event.source()):
                event.acceptProposedAction()

        def dragMoveEvent(self, event: Any) -> None:  # noqa: N802 - Qt name
            if self.takes(self.dragged_key(event.mimeData()), event.source()):
                event.acceptProposedAction()

        def dropEvent(self, event: Any) -> None:  # noqa: N802 - Qt name
            key = self.dragged_key(event.mimeData())
            if not self.takes(key, event.source()):
                return
            try:
                x = event.position().x()  # Qt6
            except AttributeError:
                x = event.pos().x()
            if self.drop(key, x, event.source()):
                event.acceptProposedAction()

        def drop(self, key: str, x: float, source: Any = None) -> bool:
            """The chip of ``key`` dropped at ``x``: moved along this rail, or handed to the owner when it comes
            from another one. True when it was taken."""
            if not self.takes(key, source):
                return False
            centres = [self._chips[name].geometry().center().x() for name in self.shown_sections() if name != key]
            index = drop_index(centres, x)
            if source is self:
                self.move(key, index)
            else:
                self.dropped_in.emit(key, index)
            return True

    return SectionRail


_SECTION_RAIL = None


def make_rail(parent: Any = None, accepts: Optional[Callable[[str], bool]] = None,
              dark: Optional[Callable[[], bool]] = None) -> Any:
    """A rail of sections (the class is made once, when Qt is there)."""
    global _SECTION_RAIL
    if _SECTION_RAIL is None:
        _SECTION_RAIL = _rail_class()
    return _SECTION_RAIL(parent, accepts, dark)
