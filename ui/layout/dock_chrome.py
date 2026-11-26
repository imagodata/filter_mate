# -*- coding: utf-8 -*-
"""The top of the dock, and two stacks of sections.

* Favorites sit in the title bar of the dock, at the right of its title; float and close are badges of the same look
  and height, drawn here rather than taken from the style (their pixmaps sat lower than the star on Windows).
* The source tag (``Vector · OGR``) sits in the layer card, at its top right; the row that held both is gone.
* Two stacks, each an accordion with the same headers: AGENT / EXPLORING above the splitter handle, FILTERING /
  EXPORTING / CONFIGURATION below. Above, one section is always open: a click on the open header leaves it open,
  the stack never folds to its headers. Below, one section is open at most, and a click on the open header folds it.
* AGENT and FILTERING do not go together: FILTERING works on what EXPLORING selects. Opening AGENT folds EXPLORING
  and FILTERING; opening FILTERING opens EXPLORING and folds AGENT. EXPORTING and CONFIGURATION stay as they are.
* The lower stack with nothing open shrinks to its headers, so the upper one takes the room.
* Between them, the splitter handle goes from one stack held to its headers and its smallest open section to the
  other: no cap on either stack (EXPLORING stopped at 700 px, the tool box at 650 px).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from qgis.PyQt.QtCore import QCoreApplication, QEvent, QObject, QPointF, QRectF, QSize, Qt
from qgis.PyQt.QtGui import QColor, QPainter, QPen, QPolygonF
from qgis.PyQt.QtWidgets import (
    QAbstractButton, QComboBox, QDockWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

logger = logging.getLogger("FilterMate")

AGENT_PAGE = "AGENT"
# The sections the user may turn off (APP.OPTIONS.<NAME>.enabled), and the buttons of the action bar acting in them.
from .section_bars import _hidden_by_code  # noqa: E402 - plain Python, no Qt at import

SECTION_PAGES = {"filtering": "FILTERING", "exporting": "EXPORTING"}
SECTION_ACTIONS = {
    # Undo and Redo stay: they walk the steps of the agent too, and open the history of the project.
    "filtering": ("pushButton_action_filter", "pushButton_action_unfilter"),
    "exporting": ("pushButton_action_export", "pushButton_action_qfieldcloud"),
}
# The source layer chooser of FILTERING, which EXPLORING follows: at the top of EXPLORING without FILTERING.
SOURCE_LAYER_WIDGETS = ("pushButton_checkable_filtering_auto_current_layer", "comboBox_filtering_current_layer")
EXPLORING_TITLE = "EXPLORING"  # a section name, never translated, as FILTERING
TITLE_BUTTON = 22  # height of everything in the title bar: favorites, float, close
TITLE_GLYPH = 8  # side of the float and close glyphs
TAG_GAP = 8


def _tr(text: str) -> str:
    return QCoreApplication.translate("DockChrome", text)


def _title_colors(dock: QDockWidget) -> tuple:
    """``(background, hover, pressed, glyph)`` of the favorites badge with no favorite, in the current theme."""
    dark = bool(getattr(getattr(dock, "_icon_manager", None), "is_dark_mode", False))
    try:
        from ..styles.mockup_design import TITLE_BADGE_PRESSED, TITLE_BADGE_TEXT, title_badge_colors
        background, hover = title_badge_colors(dark)
        return background, hover, TITLE_BADGE_PRESSED, TITLE_BADGE_TEXT
    except Exception:
        return ("#e8e8e8" if dark else "#dcdcdc"), "#ffffff", "#c8c8c8", "#555555"


class DockTitleButton(QAbstractButton):
    """Float or close, a square badge with the look of the favorites one."""

    FLOAT = "float"
    CLOSE = "close"

    def __init__(self, kind: str, dock: QDockWidget, tooltip: str, parent: QWidget) -> None:
        super().__init__(parent)
        self._kind = kind
        self._dock = dock
        self.setObjectName(f"toolButton_dock_{kind}")
        self.setFixedSize(TITLE_BUTTON, TITLE_BUTTON)
        self.setToolTip(tooltip)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)  # a repaint on enter and leave

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt name
        return QSize(TITLE_BUTTON, TITLE_BUTTON)

    def paintEvent(self, _event: Any) -> None:  # noqa: N802 - Qt name
        background, hover, pressed, glyph = _title_colors(self._dock)
        fill = pressed if self.isDown() else (hover if self.underMouse() else background)
        try:
            from ..styles.mockup_design import TITLE_BADGE_RADIUS as radius
        except Exception:
            radius = 4
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(fill))
            painter.drawRoundedRect(QRectF(self.rect()), radius, radius)
            pen = QPen(QColor(glyph), 1.4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            center = QRectF(self.rect()).center()
            half = TITLE_GLYPH / 2
            if self._kind == self.CLOSE:
                painter.drawLine(QPointF(center.x() - half, center.y() - half), QPointF(center.x() + half, center.y() + half))
                painter.drawLine(QPointF(center.x() - half, center.y() + half), QPointF(center.x() + half, center.y() - half))
            else:  # two windows, the front one lower left; the back one shows its top and right sides
                side, shift = TITLE_GLYPH - 2, 2
                left, top = center.x() - half, center.y() - half
                painter.drawRect(QRectF(left, top + shift, side, side))
                painter.drawPolyline(QPolygonF([
                    QPointF(left + shift, top + shift), QPointF(left + shift, top), QPointF(left + TITLE_GLYPH, top),
                    QPointF(left + TITLE_GLYPH, top + side), QPointF(left + side, top + side)]))
        finally:
            painter.end()


class DockTitleBar(QWidget):
    """Title, favorites, float and close: a drag or a double click acts as on any dock."""

    def __init__(self, dock: QDockWidget) -> None:
        super().__init__(dock)
        self.setObjectName("widget_dock_title_bar")
        self._dock = dock
        self.title = QLabel(dock.windowTitle(), self)
        self.title.setObjectName("label_dock_title")
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        self.title.setStyleSheet("font-weight: normal;")  # as the title of every other dock of QGIS
        self.title.setFont(dock.font())
        dock.windowTitleChanged.connect(self.title.setText)
        self.float_button = DockTitleButton(DockTitleButton.FLOAT, dock, _tr("Detach or dock the panel"), self)
        self.float_button.clicked.connect(lambda: dock.setFloating(not dock.isFloating()))
        self.close_button = DockTitleButton(DockTitleButton.CLOSE, dock, _tr("Close"), self)
        self.close_button.clicked.connect(dock.close)
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(6, 3, 3, 3)
        self._row.setSpacing(4)
        center = Qt.AlignmentFlag.AlignVCenter
        self._row.addWidget(self.title, 0, center)
        self._row.addStretch(1)
        self._slot = self._row.count()  # favorites go here
        self._row.addWidget(self.float_button, 0, center)
        self._row.addWidget(self.close_button, 0, center)
        dock.featuresChanged.connect(self._follow_features)
        self._follow_features(dock.features())

    def hold(self, widget: QWidget) -> None:
        """``widget`` at the right of the title, before the buttons of the dock, at their height."""
        widget.setParent(self)
        widget.setFixedHeight(TITLE_BUTTON)
        self._row.insertWidget(self._slot, widget, 0, Qt.AlignmentFlag.AlignVCenter)
        self._slot += 1
        widget.show()

    def _follow_features(self, features: Any) -> None:
        feature = QDockWidget.DockWidgetFeature
        self.float_button.setVisible(bool(features & feature.DockWidgetFloatable))
        self.close_button.setVisible(bool(features & feature.DockWidgetClosable))


class SourceTag(QObject):
    """The source tag at the top right of the layer card, never over its text."""

    def __init__(self, card: QLabel, tag: QWidget) -> None:
        super().__init__(card)
        self._card = card
        self._tag = tag
        tag.setParent(card)
        tag.show()
        card.installEventFilter(self)
        tag.installEventFilter(self)
        self._place()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt name
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.LayoutRequest):
            self._place()
        return False

    def _place(self) -> None:
        try:
            self._tag.adjustSize()
            width = self._tag.width()
            self._tag.move(max(0, self._card.width() - width - TAG_GAP), TAG_GAP - 2)
            self._tag.raise_()
            reserve = width + 2 * TAG_GAP
            if self._card.property("fm_tag_reserve") != reserve:
                self._card.setProperty("fm_tag_reserve", reserve)
                # Merged with the card rule of the dock sheet: only the right padding changes.
                self._card.setStyleSheet(f"QLabel#{self._card.objectName()} {{ padding-right: {reserve}px; }}")
        except RuntimeError:  # the card or the tag went with the dock
            pass


QWIDGETSIZE_MAX = 16777215
STACK_GAP = 8
SHARE_KEY = "FilterMate/splitter_top_share"  # share of the splitter the upper stack gets when both are open
TOP_KEYS = ("agent", "exploring")  # the sections of the upper stack, in their usual order
BOTTOM_KEYS = ("filtering", "exporting", "configuration")  # those of the lower stack (the pages of the tool box)
TOP_ORDER_KEY = "FilterMate/sections/top_order"  # the order the chips of each rail were dragged into
BOTTOM_ORDER_KEY = "FilterMate/sections/bottom_order"


STACKED = "stacked"  # APP.DOCKWIDGET.SECTION_HEADERS: the headers one above the other; "rail" (default): the rails


def headers_stacked(config_data: Any) -> bool:
    """``APP.DOCKWIDGET.SECTION_HEADERS`` is ``stacked``; the rails when it is absent or anything else."""
    try:
        node = config_data["APP"]["DOCKWIDGET"]["SECTION_HEADERS"]
    except (KeyError, TypeError):
        return False
    value = node.get("value") if isinstance(node, dict) else node
    return isinstance(value, str) and value.strip().lower() == STACKED


def _saved_order(key: str) -> Any:
    try:
        from qgis.PyQt.QtCore import QSettings
        return QSettings().value(key, "")
    except Exception:
        return ""


def _default_share() -> float:
    try:
        from ..config import UIConfig
        return float((UIConfig.get_config("splitter") or {}).get("initial_exploring_ratio", 0.5))
    except Exception:
        return 0.5


def _saved_share() -> float:
    """The share the user left the handle at, else the one of the display profile."""
    try:
        from qgis.PyQt.QtCore import QSettings
        value = float(QSettings().value(SHARE_KEY, -1.0))
    except (TypeError, ValueError):
        value = -1.0
    return value if 0.05 <= value <= 0.95 else _default_share()


def _save_share(share: float) -> None:
    try:
        from qgis.PyQt.QtCore import QSettings
        QSettings().setValue(SHARE_KEY, round(share, 4))
    except Exception:  # nosec B110 - not worth a message: the share is only a convenience
        pass


class SectionHeader(QPushButton):
    """A header with the look of the FILTERING one: icon on the left, name in bold, red outline when open."""

    def __init__(self, key: str, title: str, parent: QWidget) -> None:
        super().__init__(title, parent)
        self.setObjectName(f"pushButton_section_{key}")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.icon_label = None
        self.trailer = None
        try:
            from .mockup_layout import SECTION_ICON_LEFT, SECTION_TAB_HEIGHT, _section_icon_label
            self.setFixedHeight(SECTION_TAB_HEIGHT)
            self.icon_label = _section_icon_label(self)
            self._right = SECTION_ICON_LEFT
        except Exception:
            logger.debug("Section header icon not drawn", exc_info=True)
            self._right = 12

    def add_trailer(self) -> QLabel:
        """A muted label at the right of the header (where the requests of AGENT go)."""
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, self._right, 0)
        row.addStretch(1)
        self.trailer = QLabel(self)
        self.trailer.setObjectName(f"{self.objectName()}_trailer")
        self.trailer.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.trailer.setTextFormat(Qt.TextFormat.PlainText)
        row.addWidget(self.trailer)
        return self.trailer


class DockSections(QObject):
    """AGENT / EXPLORING above, FILTERING / EXPORTING / CONFIGURATION below, and the rules between them."""

    def __init__(self, dock: Any) -> None:
        super().__init__(dock)
        self._dock = dock
        self._toolbox = dock.toolBox_tabTools
        self._splitter = dock.splitter_main
        exploring = dock.frame_exploring
        index = self._splitter.indexOf(exploring)
        self.top = QWidget()
        self.top.setObjectName("widget_section_stack_top")
        self._top_layout = QVBoxLayout(self.top)
        self._top_layout.setContentsMargins(0, 0, 0, 0)
        self._top_layout.setSpacing(STACK_GAP)
        sizes = self._splitter.sizes()
        # Preferred, not the Minimum of EXPLORING: with Minimum the splitter cannot take the stack below its size
        # hint (396 px of a 905 px splitter on 1920x1200), only down to its minimum (its headers and EXPLORING's).
        policy = exploring.sizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Policy.Preferred)
        self.top.setSizePolicy(policy)
        # No cap on the lower stack either (the .ui held the tool box at 650 px: a taller zone stayed empty).
        self._toolbox.setMaximumHeight(QWIDGETSIZE_MAX)
        self._splitter.replaceWidget(index, self.top)
        if len(sizes) == self._splitter.count() and sum(sizes) > 0:
            self._splitter.setSizes(sizes)  # the manager sized the splitter for EXPLORING: the stack takes its place
        # A rail per stack lists the sections (ui/widgets/section_rail.py): one row of chips, dragged to put the
        # sections in another order. The headers stacked one above the other are the other way to list them
        # (APP.DOCKWIDGET.SECTION_HEADERS = stacked, set_stacked): the same sections, shown, open and apart as the
        # rails say; hidden otherwise, their objects stay (other code reads their icon labels).
        self._stacked = False
        self._watched = set()  # the headers of the tool box whose clicks are followed
        self._current_before_press = -1
        self.exploring_header = SectionHeader("exploring", EXPLORING_TITLE, self.top)
        self.exploring_header.hide()
        self._pages = {"exploring": exploring}
        self._headers = {"exploring": self.exploring_header}
        self._wire_top_header("exploring", self.exploring_header)
        # The keys of the sections shown in their own panel (ui/layout/section_panels.py), of either stack: out of
        # the rules of the stacks. Asked to open, a section apart has ``raise_detached`` bring its panel forward.
        self.detached = set()
        self.raise_detached = None
        self.bring_back = None  # called with the key of a section apart that is being turned off
        self.on_menu = None  # called with (key, place on the screen) on a right click on the chip of a section
        self.on_dropped = None  # called with (key, index) when the chip of a section apart is dropped on a rail
        self.on_dropped_out = None  # called with (key, place on the screen) when a chip is dropped out of every rail
        self.on_opened = None  # called when what the stacks show open may have changed (whoever changed it)
        from ..widgets.section_rail import make_rail
        self.top_rail = make_rail(self.top, accepts=lambda key: key in TOP_KEYS and key in self.detached,
                                  dark=self._dark)
        self.top_rail.setObjectName("widget_section_rail_top")
        self._top_layout.addWidget(self.top_rail)
        self._top_layout.addWidget(exploring, 1)
        exploring.show()
        self.top.show()  # QSplitter.replaceWidget leaves the new widget hidden
        self.top_rail.chosen.connect(self._on_top_chip)
        self.top_rail.reordered.connect(lambda _order: self._save_orders())
        self.top_rail.dropped_in.connect(self._on_dropped_in)
        self.top_rail.dropped_out.connect(self._on_dropped_out)
        self.top_rail.menu_requested.connect(self._on_chip_menu)
        self.top_rail.set_sections(["exploring"])
        # "Nothing open" below: QToolBox always has a current page, so an empty one, its header never shown.
        self._nothing = QWidget()
        self._nothing.setObjectName("page_no_section")
        self._toolbox.addItem(self._nothing, "")
        holder = self._nothing
        while holder is not None and holder is not self._toolbox:  # QToolBox wraps each page in a scroll area
            holder.setMaximumHeight(0)
            holder = holder.parentWidget()
        self._hidden_actions = {}
        self._reopen = set()
        self._shown = {}
        self._source_row, self._source_origins = None, []
        self._bottom_limits = self._bottom_held = None  # of the lower stack with nothing open: its own, its rail's
        self._share = _saved_share()
        self._left = None  # (share, heights of the two stacks) as the user left the handle, until the dock is resized
        self.bottom_rail = make_rail(self._toolbox.parentWidget(),
                                     accepts=lambda key: key in BOTTOM_KEYS and key in self.detached, dark=self._dark)
        self.bottom_rail.setObjectName("widget_section_rail_bottom")
        holder = _layout_holding(self._toolbox.parentWidget(), self._toolbox) if self._toolbox.parentWidget() else None
        if holder is not None:
            holder.insertWidget(holder.indexOf(self._toolbox), self.bottom_rail)
            holder.setSpacing(STACK_GAP)
        self.bottom_rail.chosen.connect(self._on_bottom_chip)
        self.bottom_rail.reordered.connect(lambda _order: self._save_orders())
        self.bottom_rail.dropped_in.connect(self._on_dropped_in)
        self.bottom_rail.dropped_out.connect(self._on_dropped_out)
        self.bottom_rail.menu_requested.connect(self._on_chip_menu)
        from ..widgets.section_rail import parse_order
        present = [key for key in BOTTOM_KEYS if getattr(dock, key.upper(), None) is not None]
        self.bottom_rail.set_sections(parse_order(_saved_order(BOTTOM_ORDER_KEY), present))
        dock._fm_rails = [self.top_rail, self.bottom_rail]  # their icons follow the theme (update_section_icons)
        self._refresh_headers()
        self._toolbox.currentChanged.connect(self._on_bottom_changed)
        self._splitter.splitterMoved.connect(self._on_handle_moved)
        self._splitter.installEventFilter(self)
        self._open_top("exploring")
        self.refresh_rails()
        self.set_stacked(headers_stacked(getattr(dock, "CONFIG_DATA", None)))

    def _dark(self) -> bool:
        return bool(getattr(getattr(self._dock, "_icon_manager", None), "is_dark_mode", False))

    # --- the rails -------------------------------------------------------------------

    def refresh_rails(self) -> None:
        """Each rail shows the chips of the sections of its stack that are in the dock: not one turned off, nor one
        shown in its own panel; the open one is checked. The lower stack goes with its last chip."""
        try:
            for key in self.top_rail.sections():
                self.top_rail.set_shown(key, key not in self.detached)
            for key in self.bottom_rail.sections():
                self.bottom_rail.set_shown(key, key not in self.detached and self._shown.get(key, True))
            self.top_rail.set_current(next((key for key in self._pages if self._open_in_stack(key)), None))
            self.bottom_rail.set_current(self.bottom_key())
            self._refresh_headers()
            self._place_layer_mirror()
            self._open_alone()
            self._fit()
        except RuntimeError:  # the dock went away
            pass

    def _open_alone(self) -> None:
        """The dock always shows one open section. In the dock as it is by default one is always open above
        (EXPLORING or AGENT). With EXPLORING in its own panel nothing has to be, and when nothing is open below
        either (the open section left for a panel, was turned off, or something opened a section that is apart) the
        dock showed folded chips and nothing else: the first section of the lower stack opens, else the one left
        above (AGENT alone in the dock)."""
        if self._anything_open():
            return
        below = self.bottom_rail.shown_sections()
        above = [key for key in self._pages if key not in self.detached]
        page = getattr(self._dock, below[0].upper(), None) if below else None
        if page is not None:
            self._toolbox.setCurrentWidget(page)
        elif above:
            self._open_top("exploring" if "exploring" in above else above[0])

    def _anything_open(self) -> bool:
        return any(self._open_in_stack(key) for key in self._pages) or self.bottom_key() is not None

    def _may_fold_top(self) -> bool:
        """What is open above may be folded: EXPLORING is in its own panel (in the dock, one section stays open
        above), and a section is open below to take the room: the last open section of the dock stays open."""
        return "exploring" in self.detached and self.bottom_key() is not None

    def _may_fold_bottom(self) -> bool:
        """What is open below may be folded: a section is open above to take the room."""
        return any(self._open_in_stack(key) for key in self._pages)

    # --- EXPLORING away from FILTERING ------------------------------------------------------------------------------

    def together(self) -> bool:
        """EXPLORING and FILTERING are in the same panel: both in the dock. Apart (one of them in its own panel
        of QGIS), EXPLORING needs a chooser of the current layer of its own: the one of FILTERING is elsewhere."""
        return "exploring" not in self.detached and "filtering" not in self.detached

    def _place_layer_mirror(self) -> None:
        """A second chooser at the top of EXPLORING while FILTERING is elsewhere or folded
        (ui/widgets/layer_chooser_mirror.py). With FILTERING turned off, its own chooser is moved to EXPLORING
        instead (``_move_source_layer``). With both sections open in the dock, its chooser is enough."""
        wanted = self._shown.get("filtering", True) and (not self.together() or self.bottom_key() != "filtering")
        mirror = getattr(self, "_layer_mirror", None)
        if not wanted:
            if mirror is not None:
                mirror.hide()
            return
        if mirror is None:
            source = getattr(self._dock, "comboBox_filtering_current_layer", None)
            holder = self._dock.frame_exploring.layout()
            if source is None or holder is None:
                return
            from ..widgets.layer_chooser_mirror import make_mirror
            mirror = self._layer_mirror = make_mirror(source, self._dock.frame_exploring, self._dock)
            holder.insertWidget(0, mirror)
            try:  # as the other lists of the dock: the wheel changes the layer only once the list has the focus
                from ..widgets.wheel_guard import guard_input_wheel
                guard_input_wheel(self._dock.frame_exploring)
            except Exception:
                logger.debug("The chooser of EXPLORING answers the wheel without the focus", exc_info=True)
        mirror.show()

    # --- the headers stacked, for who prefers them to the rails -----------------------------------------------------

    @property
    def stacked(self) -> bool:
        return self._stacked

    def set_stacked(self, stacked: bool) -> bool:
        """List the sections by headers stacked one above the other (``APP.DOCKWIDGET.SECTION_HEADERS`` =
        ``stacked``) or by a rail of chips per stack, the default. The sections shown, the open ones and those in
        their own panel stay as they are; the order dragged along a rail is the one of the rails only. True when
        it changed."""
        stacked = bool(stacked)
        if stacked == self._stacked:
            return False
        self._stacked = stacked
        try:
            self._lay_top()
            self._place_trailer()
            self.bottom_rail.setVisible(not stacked)
            self.refresh_rails()
        except RuntimeError:  # the dock went away
            pass
        return True

    def _place_trailer(self) -> None:
        """The label that says where the requests of AGENT go: at the right of the rail, or of the header of AGENT
        when the headers are stacked (hidden with the rail, it showed nowhere)."""
        label, header = getattr(self, "_agent_trailer", None), self._headers.get("agent")
        if label is None or header is None:
            return
        if self._stacked:
            row = header.layout()
            if row is None:
                row = QHBoxLayout(header)
                row.setContentsMargins(0, 0, getattr(header, "_right", 12), 0)
                row.addStretch(1)
            row.addWidget(label)
        else:
            self.top_rail.layout().addWidget(label)
        # In the header it must not take the clicks that open the section.
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self._stacked)
        label.show()

    def _lay_top(self) -> None:
        """The upper stack in order: the rail then the pages, or each header above its page. A page in its own
        panel is not in the stack."""
        layout = self._top_layout
        wanted = [(self.top_rail, 0)]
        for key in TOP_KEYS:
            header, page = self._headers.get(key), self._pages.get(key)
            if header is not None and self._stacked:
                wanted.append((header, 0))
            if page is not None and key not in self.detached:
                wanted.append((page, 1))
        for widget, stretch in wanted:  # each one out then back at the end: a widget that went away is left out,
            try:                        # the others still get their place
                if layout.indexOf(widget) >= 0:
                    layout.removeWidget(widget)
                layout.addWidget(widget, stretch)
            except RuntimeError:
                continue
        if not self._stacked:
            for header in self._headers.values():
                try:
                    if layout.indexOf(header) >= 0:
                        layout.removeWidget(header)
                except RuntimeError:
                    continue
        self.top_rail.setVisible(not self._stacked)

    def place_top(self, key: str) -> None:
        """The page of ``key`` is back from its own panel: at its place in the upper stack, folded."""
        self._lay_top()
        page = self._pages.get(key)
        if page is not None:
            page.hide()
        filtering_open = self._toolbox.currentWidget() is getattr(self._dock, "FILTERING", None)
        if key == "exploring" and filtering_open:
            # While it was away AGENT and FILTERING could be open together. Back in the dock, FILTERING works on
            # EXPLORING again, which folds AGENT: the dock as it always is, its buttons those of FILTERING.
            self._open_top("exploring")
        elif not any(self._open_in_stack(name) for name in self._pages):
            self._open_top("exploring")  # EXPLORING is back, or nothing was open while it was away

    def _wire_top_header(self, key: str, header: SectionHeader) -> None:
        header.clicked.connect(lambda _checked=False, name=key: self._on_top_header(name))
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(
            lambda pos, name=key, button=header: self._on_chip_menu(name, button.mapToGlobal(pos)))

    def _on_top_header(self, key: str) -> None:
        """A click on a folded header opens it; on the open one, it leaves it open (and checked: the click
        unchecked it), or folds it when nothing has to stay open above (``_on_top_chip``)."""
        if self._open_in_stack(key):
            if self._may_fold_top():
                self._open_top(None)
            else:
                self._headers[key].setChecked(True)
            return
        self.open_top(key)

    def _told_open(self) -> None:
        """Another section may be open, or none: the panels compare it with what was (a click on the open chip
        changes nothing) and size the dock again when it changed."""
        if self.on_opened is not None:
            self.on_opened()

    def _bottom_headers(self) -> list:
        """The headers QToolBox gives its pages, the one of "nothing open" left out."""
        return [button for button in self._toolbox.findChildren(QAbstractButton)
                if button.objectName() == "qt_toolbox_toolboxbutton" and button.text() != ""]

    def _refresh_headers(self) -> None:
        """Stacked: a header for each section the rails show, the open one of the upper stack checked. Otherwise
        none: the rails list the sections."""
        for key, header in self._headers.items():
            header.setVisible(self._stacked and key not in self.detached)
            header.setChecked(self._open_in_stack(key))
        exploring = self._headers.get("exploring")
        if exploring is not None:
            exploring.setToolTip("" if self._open_in_stack("exploring") else _tr("Show EXPLORING"))
        shown = ({key for key in BOTTOM_KEYS if key not in self.detached and self._shown.get(key, True)}
                 if self._stacked else set())
        titles = {self._toolbox.itemText(self._toolbox.indexOf(page)): key for key in BOTTOM_KEYS
                  for page in [getattr(self._dock, key.upper(), None)]
                  if page is not None and self._toolbox.indexOf(page) >= 0}
        for button in self._toolbox.findChildren(QAbstractButton):
            if button.objectName() != "qt_toolbox_toolboxbutton":
                continue
            key = titles.get(button.text())
            button.setVisible(key in shown)  # never the header of "nothing open"
            if key is None or button in self._watched:
                continue
            self._watched.add(button)
            button.pressed.connect(lambda: setattr(self, "_current_before_press", self._toolbox.currentIndex()))
            button.clicked.connect(lambda _checked=False, item=button: self._on_bottom_header(item))
            button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            button.customContextMenuRequested.connect(
                lambda pos, name=key, item=button: self._on_chip_menu(name, item.mapToGlobal(pos)))

    def _on_bottom_header(self, button: QAbstractButton) -> None:
        """A click on the open header folds the stack. QToolBox has already made the page of the header current
        (its own slot comes first): what was open is the page kept at the press."""
        for index in range(self._toolbox.count()):
            if self._toolbox.itemText(index) == button.text():
                if index == self._current_before_press and self._may_fold_bottom():  # not the last one open
                    self._toolbox.setCurrentWidget(self._nothing)
                elif index == self._current_before_press:
                    self._refresh_headers()
                return

    def bottom_key(self) -> Optional[str]:
        """The section open in the lower stack, None with none open."""
        current = self._toolbox.currentWidget()
        for key in BOTTOM_KEYS:
            if current is not None and current is getattr(self._dock, key.upper(), None):
                return key
        return None

    def _save_orders(self) -> None:
        """The order the user dragged the chips into, for this session and the next ones."""
        try:
            from qgis.PyQt.QtCore import QSettings
            from ..widgets.section_rail import format_order
            settings = QSettings()
            settings.setValue(TOP_ORDER_KEY, format_order(self.top_rail.sections()))
            settings.setValue(BOTTOM_ORDER_KEY, format_order(self.bottom_rail.sections()))
        except Exception:  # nosec B110 - a convenience: the usual order next time
            pass

    def _on_chip_menu(self, key: str, place: Any) -> None:
        if self.on_menu is not None:
            self.on_menu(key, place)

    def _on_dropped_in(self, key: str, index: int) -> None:
        """The chip of a section apart was dropped on the rail of its stack: the section comes back, there."""
        if self.on_dropped is None:
            return
        self.on_dropped(key, index)
        rail = self.top_rail if key in TOP_KEYS else self.bottom_rail
        rail.move(key, index)

    def _on_dropped_out(self, key: str, place: Any) -> None:
        """A chip of the dock was dropped where no rail and no panel took it: the panels decide (a new one)."""
        if self.on_dropped_out is not None:
            self.on_dropped_out(key, place)

    # --- the top stack ---------------------------------------------------------------

    def add_agent(self, page: QWidget) -> QLabel:
        """AGENT in the top stack, folded: its chip in the rail, and the label at the right of the rail."""
        header = SectionHeader("agent", AGENT_PAGE, self.top)
        header.hide()  # as the header of EXPLORING: shown when the headers are stacked
        self._pages["agent"] = page
        self._headers["agent"] = header
        self._wire_top_header("agent", header)
        self._lay_top()
        page.hide()
        from ..widgets.section_rail import parse_order
        self.top_rail.set_sections(parse_order(_saved_order(TOP_ORDER_KEY), TOP_KEYS))
        trailer = self._agent_trailer = self.top_rail.trailer()
        self._place_trailer()
        self.refresh_rails()
        return trailer

    def is_open(self, key: str) -> bool:
        """In view: open in its stack, or on screen in its own panel (behind another tab, it is not).

        Qt calls the page of a panel behind another tab visible (``isVisible`` is true in Qt 5 and 6): only its
        visible region, empty then, tells that nobody sees it."""
        page = self._pages.get(key)
        if page is None:
            return False
        if key in self.detached:
            return page.isVisible() and not page.visibleRegion().isEmpty()
        return not page.isHidden()

    def in_view(self, key: str) -> bool:
        """Open, and on screen. The dock itself can be behind the tab of another panel of QGIS (Layers), with its
        section open in it: open then, and seen by nobody."""
        page = self._pages.get(key)
        return bool(page is not None and self.is_open(key) and page.isVisible()
                    and not page.visibleRegion().isEmpty())

    def bring_in_view(self, key: str) -> None:
        """``key`` open (``open_top``: its panel comes forward when it has one), and the dock in front of the tabs
        it shares with other panels when the section is in it."""
        self.open_top(key)
        if key in self.detached:
            return
        try:
            if self._dock.isVisible() and not self._dock.isFloating():
                self._dock.raise_()
        except RuntimeError:  # the dock went away
            pass

    def _open_in_stack(self, key: str) -> bool:
        """Open in the stack of the dock; a section in its own panel is not, wherever it shows."""
        page = self._pages.get(key)
        return page is not None and key not in self.detached and not page.isHidden()

    def open_top(self, key: Optional[str]) -> None:
        """Open ``key`` in the top stack and apply the rules. One section of it stays open: None, or a section
        that is not there, opens EXPLORING. A section in its own panel has that panel come forward instead."""
        if key in self.detached:
            if self.raise_detached is not None:
                self.raise_detached(key)
            return
        if (key == "agent" and "exploring" not in self.detached
                and self._toolbox.currentWidget() is getattr(self._dock, "FILTERING", None)):
            # FILTERING works on EXPLORING, which AGENT folds. Not with EXPLORING in its own panel: it stays in view.
            self._toolbox.setCurrentWidget(self._nothing)
        self._open_top(key)

    def _open_top(self, key: Optional[str]) -> None:
        if key not in self._pages or key in self.detached:  # never nothing open above
            key = "exploring"
        if key in self.detached:
            key = None  # but with EXPLORING in its own panel: what is left above (AGENT) may be folded
        for name, page in self._pages.items():
            if name in self.detached:
                continue
            page.setVisible(name == key)
        self.top_rail.set_current(key)
        self._refresh_headers()
        manager = getattr(self._dock, "_action_bar_manager", None)
        if manager is not None:  # with AGENT open, Undo, Redo and Compare are shown: they walk its steps
            try:
                manager.sync_sections()
            except RuntimeError:  # the dock went away
                pass
        self._fit()
        request = getattr(self._dock, "undoRedoStateRequested", None)
        if request is not None:  # Undo and Redo follow AGENT when it opens or folds
            try:
                request.emit()
            except (RuntimeError, TypeError):
                pass
        self._told_open()

    def _on_top_chip(self, key: str) -> None:
        """A click on the chip of a folded section opens it; on the open one, it leaves it open: one section
        stays open above. With EXPLORING in its own panel the open one (AGENT) folds, as a section below does:
        nothing has to stay open there, and the lower stack takes the room. Not when it is the only section of the
        dock."""
        if not self._open_in_stack(key):
            self.open_top(key)
        elif self._may_fold_top():
            self._open_top(None)

    # --- the bottom stack ------------------------------------------------------------

    def _on_bottom_chip(self, key: str) -> None:
        """A click on a chip opens its section; on the chip of the open one, it folds the stack (not when nothing
        is open above: the dock would show its chips and nothing else)."""
        page = getattr(self._dock, key.upper(), None)
        if page is None:
            return
        fold = self._toolbox.currentWidget() is page and self._may_fold_bottom()
        self._toolbox.setCurrentWidget(self._nothing if fold else page)
        if not fold:
            self.bottom_rail.set_current(self.bottom_key())  # the click on the open chip unchecked it

    def _on_bottom_changed(self, _index: int) -> None:
        current = self._toolbox.currentWidget()
        if any(current is getattr(self._dock, key.upper(), None) for key in self.detached):
            return  # a section in its own panel: that panel comes forward (section_panels.py), the stacks stay
        if (self._toolbox.currentWidget() is getattr(self._dock, "FILTERING", None)
                and "exploring" not in self.detached and not self.is_open("exploring")):
            # FILTERING works on what EXPLORING selects. In its own panel EXPLORING stays where the user put it
            # (it may be behind a tab on purpose), and AGENT stays open beside FILTERING.
            self._open_top("exploring")
        self.bottom_rail.set_current(self.bottom_key())
        self._place_layer_mirror()
        self._fit()
        self._told_open()

    # --- sections turned off (APP.OPTIONS.FILTERING / EXPORTING .enabled) -----------

    def set_section_shown(self, key: str, shown: bool) -> bool:
        """Show or hide FILTERING or EXPORTING: its header, and the buttons of the action bar that act in it only.
        Without FILTERING the source layer chooser goes to the top of EXPLORING, which still follows it. Hiding again
        hides a button made since (QFieldCloud comes after the dock). True when the section was there."""
        page = getattr(self._dock, SECTION_PAGES.get(key, ""), None)
        index = self._toolbox.indexOf(page) if page is not None else -1
        if index < 0:
            return False
        if not shown and key in self.detached and self.bring_back is not None:
            self.bring_back(key)  # in its own panel (section_panels.py): a section turned off shows nowhere
        if not shown and self._toolbox.currentWidget() is page:
            self._reopen.add(key)  # open again when it comes back, if nothing else was opened meanwhile
            self._toolbox.setCurrentWidget(self._nothing)
        self._toolbox.setItemEnabled(index, shown)
        self._shown[key] = shown
        self.refresh_rails()  # its chip goes from the rail, or comes back
        hidden = self._hidden_actions.setdefault(key, {})
        bars = []
        for name in SECTION_ACTIONS.get(key, ()):
            widget = getattr(self._dock, name, None)
            if widget is None:
                continue
            if not shown:
                if name not in hidden:
                    # QFieldCloud stays hidden without its plugin. A button just made, or one a bar rebuilt in the
                    # same turn (another position of the bar) took and gives back, is hidden for a moment only.
                    hidden[name] = not _hidden_by_code(widget)
                widget.setVisible(False)
            elif name in hidden:
                widget.setVisible(hidden.pop(name))
            bar = widget.parentWidget().layout() if widget.parentWidget() is not None else None
            if bar is not None and bar not in bars:
                bars.append(bar)
        for bar in bars:
            _even_spacing(bar)
        if key == "filtering":
            self._move_source_layer(to_exploring=not shown)
        if shown and key in self._reopen:
            self._reopen.discard(key)
            # Not over AGENT: opening FILTERING opens EXPLORING, which would fold AGENT under its user. AGENT in
            # its own panel folds nothing, nor does it with EXPLORING in its own.
            folds_agent = self._open_in_stack("agent") and "exploring" not in self.detached
            if self._toolbox.currentWidget() is self._nothing and not folds_agent:
                self._toolbox.setCurrentWidget(page)
        self._fit()
        return True

    def section_shown(self, key: str) -> bool:
        """As last set here (a disabled parent would make ``QToolBox.isItemEnabled`` say hidden)."""
        return self._shown.get(key, True)

    def _move_source_layer(self, to_exploring: bool) -> None:
        """The same widgets, moved: everything wired to them keeps working, nothing to keep in step."""
        widgets = [getattr(self._dock, name, None) for name in SOURCE_LAYER_WIDGETS]
        if any(widget is None for widget in widgets):
            return
        if to_exploring:
            holder = self._dock.frame_exploring.layout()
            if self._source_row is not None or holder is None:
                return
            origins = []
            for widget in widgets:
                layout = _layout_holding(widget.parentWidget(), widget) if widget.parentWidget() else None
                if layout is None:
                    return  # not where the .ui puts it: left alone
                at = layout.indexOf(widget)
                stretch = layout.stretch(at) if hasattr(layout, "stretch") else 0
                origins.append((widget, layout, at, stretch, layout.itemAt(at).alignment(), widget.isHidden()))
            row = QWidget(self._dock.frame_exploring)
            row.setObjectName("widget_exploring_source_layer")
            line = QHBoxLayout(row)
            line.setContentsMargins(0, 0, 0, 0)
            line.setSpacing(4)
            for widget, layout, *_rest in origins:
                layout.removeWidget(widget)
                line.addWidget(widget, 1 if isinstance(widget, QComboBox) else 0)
                widget.setVisible(not _rest[-1])
            holder.insertWidget(0, row)
            row.show()
            self._source_row, self._source_origins = row, origins
            return
        if self._source_row is None:
            return
        for widget, layout, at, stretch, alignment, was_hidden in self._source_origins:  # back, as they were
            self._source_row.layout().removeWidget(widget)
            layout.insertWidget(min(at, layout.count()), widget, stretch, alignment)
            widget.setVisible(not was_hidden)
        self._source_row.hide()
        self._source_row.deleteLater()
        self._source_row, self._source_origins = None, []

    # --- room ------------------------------------------------------------------------

    def _fit(self) -> None:
        """A stack with nothing open keeps its rail only, and the other one takes the room. The lower stack with no
        chip left (its sections are turned off, or in their own panels) goes altogether."""
        try:
            top_open = any(self._open_in_stack(key) for key in self._pages)
            self.top.setVisible(any(key not in self.detached for key in self._pages))  # AGENT and EXPLORING apart
            self.top.setMaximumHeight(QWIDGETSIZE_MAX if top_open else self._headers_height())
            bottom = self._splitter.widget(1) if self._splitter.count() > 1 else None
            if bottom is not None:
                bottom.setVisible(bool(self.bottom_rail.shown_sections()))
                nothing = self._toolbox.currentWidget() is self._nothing
                if nothing:
                    if self._bottom_limits is None:  # what the dimension managers set: given back when a section opens
                        self._bottom_limits = (bottom.minimumHeight(), bottom.maximumHeight())
                    height = self._bottom_headers_height(bottom)
                    self._bottom_held = (min(self._bottom_limits[0], height), height)
                    # The minimum first: Qt keeps the larger of the two, and the rail would be spread over it.
                    bottom.setMinimumHeight(self._bottom_held[0])
                    bottom.setMaximumHeight(height)
                elif self._bottom_limits is not None:
                    bottom.setMaximumHeight(self._bottom_limits[1])
                    bottom.setMinimumHeight(self._bottom_limits[0])
                    self._bottom_limits = self._bottom_held = None
                self._hold_toolbox(nothing)
                sizes = self._splitter.sizes()
                total = self._room()
                if len(sizes) == 2 and total > 0:
                    # A stack held to its headers gives the rest to the other one at once.
                    if not top_open:
                        self._splitter.setSizes([self.top.maximumHeight(), total - self.top.maximumHeight()])
                    elif nothing:
                        self._splitter.setSizes([total - bottom.maximumHeight(), bottom.maximumHeight()])
                    else:
                        self._share_room()  # both open again: the share the handle was left at
        except RuntimeError:  # the dock went away
            pass

    def dimensions_applied(self) -> None:
        """A display profile, or a theme, just gave the dock its dimensions again: the limits kept for the lower
        stack while nothing is open in it are those of before, and the stack is no longer held to its rail (a band
        of 150 to 240 px stayed empty under it, and the older limits came back with the next section opened).

        Only a limit a manager set again replaces the one kept: the splitter manager sets the minimum alone, after
        the dimensions. The maximum the stack was still held to, its rail, was then kept as its own: the next
        section opened in a stack 150 px high that the handle could not enlarge (a maximum of 34 px under a
        minimum of 150), its rows scrolled."""
        try:
            bottom = self._splitter.widget(1) if self._splitter.count() > 1 else None
            if self._bottom_limits is not None and self._bottom_held is not None and bottom is not None:
                least, most = bottom.minimumHeight(), bottom.maximumHeight()
                self._bottom_limits = (self._bottom_limits[0] if least == self._bottom_held[0] else least,
                                       self._bottom_limits[1] if most == self._bottom_held[1] else most)
            else:
                self._bottom_limits = None
            self._toolbox_minimum = None
            self.refresh_rails()
        except RuntimeError:  # the dock went away
            pass

    def _hold_toolbox(self, nothing: bool) -> None:
        """With nothing open the tool box takes no room: its headers are gone (the rail above it lists the
        sections), and its minimum, sized for them, would keep an empty band under the rail. With the headers
        stacked it stays, held to the headers it shows: its own minimum (150 px, more than three headers need)
        spread them apart and cut the last one."""
        if not self._stacked:
            self._restore_toolbox_minimum()
            self._toolbox.setVisible(not nothing)
            return
        self._toolbox.setVisible(True)
        shown = [button for button in self._bottom_headers() if not button.isHidden()]
        if nothing:
            if getattr(self, "_toolbox_minimum", None) is None:
                self._toolbox_minimum = self._toolbox.minimumHeight()
            layout = self._toolbox.layout()
            spacing = max(0, layout.spacing()) if layout is not None else 0
            margins = layout.contentsMargins() if layout is not None else None
            height = sum(header.maximumHeight() for header in shown) + spacing * len(shown)
            if margins is not None:
                height += margins.top() + margins.bottom()
            self._toolbox.setMinimumHeight(min(self._toolbox_minimum, height))
        else:
            self._restore_toolbox_minimum()

    def _restore_toolbox_minimum(self) -> None:
        saved = getattr(self, "_toolbox_minimum", None)
        if saved is not None:
            self._toolbox.setMinimumHeight(saved)
            self._toolbox_minimum = None

    def _room(self) -> int:
        """The room the two stacks share. What the splitter gives them now, or its own length when that is more:
        a stack that comes back from hidden (AGENT merged back after AGENT and EXPLORING were both in panels) has
        no size yet, and with the other one held to its rail the sizes add up to that rail alone. AGENT then
        opened 0 px high (2026-11-17, found by the walk of the bench through the layouts)."""
        sizes = self._splitter.sizes()
        length = self._splitter.height() - self._splitter.handleWidth() * max(0, len(sizes) - 1)
        return max(sum(sizes), length)

    def _both_open(self) -> bool:
        return (any(self._open_in_stack(key) for key in self._pages)
                and self._toolbox.currentWidget() is not self._nothing)

    def _share_room(self) -> None:
        """Both stacks open: the top one gets ``self._share`` of the room (Qt keeps each one above its minimum).

        Where the user left the handle, in a dock that kept its height since, the two stacks get the heights they
        were left at: the share is taken of a room that counts the margins of the splitter (16 px more than the
        stacks get), and a handle left at 319 px came back at 310 px with the next section opened."""
        sizes = self._splitter.sizes()
        total = self._room()
        if len(sizes) == 2 and total > 0:
            if self._left is not None and self._left[0] == self._share and sum(self._left[1]) == sum(sizes):
                self._splitter.setSizes(self._left[1])
                return
            top = int(round(total * self._share))
            self._splitter.setSizes([top, total - top])

    def _on_handle_moved(self, _pos: int, _index: int) -> None:
        """The user dragged the handle: that share is kept, in this session and the next ones."""
        try:
            sizes = self._splitter.sizes()
            if len(sizes) != 2 or sum(sizes) <= 0 or not self._both_open():
                return
            self._share = sizes[0] / sum(sizes)
            self._left = (self._share, list(sizes))
            _save_share(self._share)
        except RuntimeError:
            pass

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt name
        # A taller or shorter dock keeps the share (QSplitter gave the difference to the upper stack: at startup,
        # on 1920x1200, FILTERING was held to its minimum and scrolled).
        if watched is self._splitter and event.type() == QEvent.Type.Resize:
            try:
                if event.size().height() != event.oldSize().height():
                    self._left = None  # another room: the share alone says where the handle goes
                if self._both_open():
                    self._share_room()
            except RuntimeError:
                pass
        return False

    def _bottom_headers_height(self, bottom: QWidget) -> int:
        """The lower stack with nothing open: its rail and the margins around; with the headers stacked, the
        headers shown, the gaps between them and the margins around."""
        if self._stacked:
            buttons = [button for button in self._bottom_headers() if not button.isHidden()]
            try:
                from .mockup_layout import SECTION_TAB_HEIGHT
            except Exception:
                SECTION_TAB_HEIGHT = 34
            for button in buttons:
                button.setMaximumHeight(SECTION_TAB_HEIGHT)  # QToolBox would stretch them over the room left
            spacing = self._toolbox.layout().spacing() if self._toolbox.layout() is not None else 0
            height = len(buttons) * SECTION_TAB_HEIGHT + max(0, spacing) * len(buttons)
            widget = self._toolbox
        else:
            height = self.bottom_rail.height()
            widget = self.bottom_rail.parentWidget()
        while widget is not None and widget is not bottom.parentWidget():
            layout = widget.layout()
            if layout is not None:
                margins = layout.contentsMargins()
                height += margins.top() + margins.bottom()
            widget = widget.parentWidget()
        return height

    def _headers_height(self) -> int:
        if not self._stacked:
            return self.top_rail.height()
        headers = [header for header in self._headers.values() if not header.isHidden()]
        return sum(header.height() for header in headers) + STACK_GAP * max(0, len(headers) - 1)


def _layout_holding(widget: QWidget, child: QWidget):
    """The layout, nested at any depth under ``widget``, that holds ``child``; None when none does."""
    pending = [widget.layout()] if widget.layout() is not None else []
    while pending:
        layout = pending.pop()
        if layout.indexOf(child) >= 0:
            return layout
        for position in range(layout.count()):
            inner = layout.itemAt(position).layout()
            if inner is not None:
                pending.append(inner)
    return None


def _even_spacing(layout) -> None:
    try:
        from .action_bar_manager import even_action_spacing
        even_action_spacing(layout)
    except Exception:
        logger.debug("Action bar not spaced again", exc_info=True)


def section_enabled(config_data: Any, key: str) -> bool:
    """``APP.OPTIONS.<FILTERING|EXPORTING>.enabled``; on when absent, as in the default configuration."""
    try:
        node = config_data["APP"]["OPTIONS"][SECTION_PAGES[key]]["enabled"]
    except (KeyError, TypeError):
        return True
    value = node.get("value") if isinstance(node, dict) else node
    if isinstance(value, str):
        return value.strip().lower() not in ("false", "0", "no", "off")
    return value is not False and value != 0


def apply_section_options(dock: Any) -> list:
    """Show or hide FILTERING and EXPORTING as the configuration says, and list the sections by rails or by headers
    stacked (``APP.DOCKWIDGET.SECTION_HEADERS``), and lay out the rows of FILTERING and EXPORTING
    (``APP.DOCKWIDGET.SECTION_HEIGHT``); the keys of the sections whose state changed, ``headers`` when the way they
    are listed did, ``height`` when the rows were laid out another way, ``sizing`` when ``PANEL_SIZING`` changed."""
    sections = getattr(dock, "_fm_sections", None)
    config_data = getattr(dock, "CONFIG_DATA", None) or {}
    if sections is None:
        return _apply_panel_sizing(dock, config_data, _apply_section_height(dock, config_data, []))
    changed = []
    for key in SECTION_PAGES:
        wanted = section_enabled(config_data, key)
        try:
            before = sections.section_shown(key)
            # Hidden again even when it was: a button of the section made since is hidden with it.
            if (before != wanted or not wanted) and sections.set_section_shown(key, wanted) and before != wanted:
                changed.append(key)
        except RuntimeError:  # the dock went away
            return changed
    if changed:
        _follow_sections(dock)
    try:
        if sections.set_stacked(headers_stacked(config_data)):
            changed.append("headers")  # listed another way: nothing left the dock nor came back
            manager = getattr(dock, "_action_bar_manager", None)
            if manager is not None:
                manager.sync_sections()
    except RuntimeError:  # the dock went away
        pass
    return _apply_panel_sizing(dock, config_data, _apply_section_height(dock, config_data, changed))


def _apply_panel_sizing(dock: Any, config_data: Any, changed: list) -> list:
    """``changed`` with ``sizing`` added when ``APP.DOCKWIDGET.PANEL_SIZING`` changed since the last call (the
    panels are sized again at once when it is back to ``auto``: the caller asks for it, see config_controller.py)."""
    try:
        from .section_panels import panel_sizing
        mode = panel_sizing(config_data)
        if dock.property("fm_panel_sizing") not in (None, mode):
            changed.append("sizing")
            panels = getattr(dock, "_fm_panels", None)
            if panels is not None:  # heights and widths noted under the other mode are not used
                panels.forget_sizes()
        dock.setProperty("fm_panel_sizing", mode)
    except Exception as exc:  # the dock went away (RuntimeError): no other change is lost
        logger.debug(f"Panel sizing not followed: {exc}")
    return changed


def _apply_section_height(dock: Any, config_data: Any, changed: list) -> list:
    """The rows of FILTERING and EXPORTING one gap apart, or spread (``APP.DOCKWIDGET.SECTION_HEIGHT``): ``changed``
    with ``height`` added when they were laid out another way. A failure here loses no other change."""
    try:
        from .mockup_layout import lay_out_rows, section_height
        mode = section_height(config_data)
        if dock.property("fm_section_height") != mode and lay_out_rows(dock, mode):
            changed.append("height")
    except Exception as exc:  # the dock went away (RuntimeError), or a form without the rows
        logger.warning(f"Rows of the sections not laid out: {exc}")
    return changed


def _follow_sections(dock: Any) -> None:
    """After a section was turned on or off: one that was in its own panel before it was turned off goes there
    again, and the buttons go where the sections left can carry them (section_panels.py, section_bars.py)."""
    try:
        panels = getattr(dock, "_fm_panels", None)
        if panels is not None:
            panels.restore()
            panels.keep_one_in_dock()  # the section turned off was the last one of the dock: one comes back
        manager = getattr(dock, "_action_bar_manager", None)
        if manager is not None:
            manager.sync_sections()
    except RuntimeError:  # the dock went away
        pass
    except Exception:
        logger.exception("Panels and buttons did not follow the sections turned on or off")


def install_dock_chrome(dock: Any) -> Optional[DockTitleBar]:
    """Title bar with favorites, the two stacks of sections; the header row goes. None when it could not be set up."""
    try:
        bar = DockTitleBar(dock)
        dock.setTitleBarWidget(bar)
        favorites = getattr(dock, "favorites_indicator_label", None)
        if favorites is not None:
            bar.hold(favorites)
        header = getattr(dock, "frame_header", None)
        if header is not None:
            header.setVisible(False)
        dock._fm_title_bar = bar
    except Exception:  # the dock keeps its usual title bar
        logger.exception("Dock title bar could not be set up")
        bar = None
    try:
        if all(getattr(dock, name, None) is not None for name in ("frame_exploring", "toolBox_tabTools", "splitter_main")):
            dock._fm_sections = DockSections(dock)
            dock._fm_exploring_icon_label = dock._fm_sections.exploring_header.icon_label
    except Exception:
        logger.exception("Section stacks could not be set up")
    return bar


def put_source_tag_in_card(dock: Any, card: QLabel) -> None:
    """The source tag of ``dock`` at the top right of ``card``."""
    tag = getattr(dock, "backend_indicator_label", None)
    if tag is None or getattr(dock, "_fm_source_tag", None) is not None:
        return
    try:
        dock._fm_source_tag = SourceTag(card, tag)
    except Exception:
        logger.exception("Source tag could not be put in the layer card")
