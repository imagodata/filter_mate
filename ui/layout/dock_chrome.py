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
    QAbstractButton, QDockWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

logger = logging.getLogger("FilterMate")

AGENT_PAGE = "AGENT"
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
        self.exploring_header = SectionHeader("exploring", EXPLORING_TITLE, self.top)
        self._top_layout.addWidget(self.exploring_header)
        self._top_layout.addWidget(exploring, 1)
        exploring.show()
        self.top.show()  # QSplitter.replaceWidget leaves the new widget hidden
        self._pages = {"exploring": exploring}
        self._headers = {"exploring": self.exploring_header}
        self.exploring_header.clicked.connect(lambda: self._on_top_header("exploring"))
        # "Nothing open" below: QToolBox always has a current page, so an empty one, its header never shown.
        self._nothing = QWidget()
        self._nothing.setObjectName("page_no_section")
        self._toolbox.addItem(self._nothing, "")
        holder = self._nothing
        while holder is not None and holder is not self._toolbox:  # QToolBox wraps each page in a scroll area
            holder.setMaximumHeight(0)
            holder = holder.parentWidget()
        self._watched = set()
        self._bottom_limits = None
        self._current_before_press = -1
        self._share = _saved_share()
        self._watch_bottom_headers()
        self._toolbox.currentChanged.connect(self._on_bottom_changed)
        self._splitter.splitterMoved.connect(self._on_handle_moved)
        self._splitter.installEventFilter(self)
        self._open_top("exploring")

    # --- the top stack ---------------------------------------------------------------

    def add_agent(self, page: QWidget) -> QLabel:
        """AGENT before EXPLORING, folded: the label at the right of its header."""
        header = SectionHeader("agent", AGENT_PAGE, self.top)
        trailer = header.add_trailer()
        self._top_layout.insertWidget(0, header)
        self._top_layout.insertWidget(1, page, 1)
        page.hide()
        self._pages["agent"] = page
        self._headers["agent"] = header
        header.clicked.connect(lambda: self._on_top_header("agent"))
        self._fit()
        return trailer

    def is_open(self, key: str) -> bool:
        page = self._pages.get(key)
        return page is not None and not page.isHidden()

    def open_top(self, key: Optional[str]) -> None:
        """Open ``key`` in the top stack and apply the rules. One section of it stays open: None, or a section
        that is not there, opens EXPLORING."""
        if key == "agent" and self._toolbox.currentWidget() is getattr(self._dock, "FILTERING", None):
            self._toolbox.setCurrentWidget(self._nothing)  # FILTERING works on EXPLORING, which AGENT folds
        self._open_top(key)

    def _open_top(self, key: Optional[str]) -> None:
        if key not in self._pages:  # never nothing open above
            key = "exploring"
        for name, page in self._pages.items():
            page.setVisible(name == key)
            self._headers[name].setChecked(name == key)
        header = self._headers["exploring"]
        header.setToolTip("" if key == "exploring" else _tr("Show EXPLORING"))
        self._fit()
        request = getattr(self._dock, "undoRedoStateRequested", None)
        if request is not None:  # Undo and Redo follow AGENT when it opens or folds
            try:
                request.emit()
            except (RuntimeError, TypeError):
                pass

    def _on_top_header(self, key: str) -> None:
        """A click on a folded header opens it; on the open one, it leaves it open (and checked: the click
        unchecked it)."""
        if self.is_open(key):
            self._headers[key].setChecked(True)
            return
        self.open_top(key)

    # --- the bottom stack ------------------------------------------------------------

    def _watch_bottom_headers(self) -> None:
        for button in self._toolbox.findChildren(QAbstractButton):
            if button.objectName() != "qt_toolbox_toolboxbutton" or button in self._watched:
                continue
            self._watched.add(button)
            if button.text() == "":
                button.hide()  # the header of "nothing open"
                continue
            button.pressed.connect(lambda: setattr(self, "_current_before_press", self._toolbox.currentIndex()))
            button.clicked.connect(lambda _checked=False, item=button: self._on_bottom_header(item))

    def _on_bottom_header(self, button: QAbstractButton) -> None:
        """A click on the open header folds the stack."""
        index = self._index_of(button)
        if index >= 0 and index == self._current_before_press:
            self._toolbox.setCurrentWidget(self._nothing)

    def _index_of(self, button: QAbstractButton) -> int:
        for index in range(self._toolbox.count()):
            if self._toolbox.itemText(index) == button.text():
                return index
        return -1

    def _on_bottom_changed(self, _index: int) -> None:
        if self._toolbox.currentWidget() is getattr(self._dock, "FILTERING", None) and not self.is_open("exploring"):
            self._open_top("exploring")  # FILTERING works on what EXPLORING selects
        self._fit()

    # --- room ------------------------------------------------------------------------

    def _fit(self) -> None:
        """A stack with nothing open keeps its headers only, and the other one takes the room."""
        try:
            top_open = any(self.is_open(key) for key in self._pages)
            self.top.setMaximumHeight(QWIDGETSIZE_MAX if top_open else self._headers_height())
            bottom = self._splitter.widget(1) if self._splitter.count() > 1 else None
            if bottom is not None:
                nothing = self._toolbox.currentWidget() is self._nothing
                if nothing:
                    if self._bottom_limits is None:  # what the dimension managers set: given back when a section opens
                        self._bottom_limits = (bottom.minimumHeight(), bottom.maximumHeight())
                    height = self._bottom_headers_height(bottom)
                    # The minimum first: Qt keeps the larger of the two, and the headers would spread over it.
                    bottom.setMinimumHeight(min(self._bottom_limits[0], height))
                    bottom.setMaximumHeight(height)
                elif self._bottom_limits is not None:
                    bottom.setMaximumHeight(self._bottom_limits[1])
                    bottom.setMinimumHeight(self._bottom_limits[0])
                    self._bottom_limits = None
                sizes = self._splitter.sizes()
                total = sum(sizes)
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

    def _both_open(self) -> bool:
        return any(self.is_open(key) for key in self._pages) and self._toolbox.currentWidget() is not self._nothing

    def _share_room(self) -> None:
        """Both stacks open: the top one gets ``self._share`` of the room (Qt keeps each one above its minimum)."""
        sizes = self._splitter.sizes()
        total = sum(sizes)
        if len(sizes) == 2 and total > 0:
            top = int(round(total * self._share))
            self._splitter.setSizes([top, total - top])

    def _on_handle_moved(self, _pos: int, _index: int) -> None:
        """The user dragged the handle: that share is kept, in this session and the next ones."""
        try:
            sizes = self._splitter.sizes()
            if len(sizes) != 2 or sum(sizes) <= 0 or not self._both_open():
                return
            self._share = sizes[0] / sum(sizes)
            _save_share(self._share)
        except RuntimeError:
            pass

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt name
        # A taller or shorter dock keeps the share (QSplitter gave the difference to the upper stack: at startup,
        # on 1920x1200, FILTERING was held to its minimum and scrolled).
        if watched is self._splitter and event.type() == QEvent.Type.Resize:
            try:
                if self._both_open():
                    self._share_room()
            except RuntimeError:
                pass
        return False

    def _bottom_headers_height(self, bottom: QWidget) -> int:
        """The lower stack with nothing open: its headers, the gaps between them and the margins around."""
        buttons = [button for button in self._toolbox.findChildren(QAbstractButton)
                   if button.objectName() == "qt_toolbox_toolboxbutton" and not button.isHidden()]
        try:
            from .mockup_layout import SECTION_TAB_HEIGHT
        except Exception:
            SECTION_TAB_HEIGHT = 34
        for button in buttons:
            button.setMaximumHeight(SECTION_TAB_HEIGHT)  # QToolBox would stretch them over the room left
        spacing = self._toolbox.layout().spacing() if self._toolbox.layout() is not None else 0
        height = len(buttons) * SECTION_TAB_HEIGHT + max(0, spacing) * len(buttons)
        widget = self._toolbox
        while widget is not None and widget is not bottom.parentWidget():
            layout = widget.layout()
            if layout is not None:
                margins = layout.contentsMargins()
                height += margins.top() + margins.bottom()
            widget = widget.parentWidget()
        return height

    def _headers_height(self) -> int:
        headers = [header for header in self._headers.values() if not header.isHidden()]
        return sum(header.height() for header in headers) + STACK_GAP * max(0, len(headers) - 1)


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
