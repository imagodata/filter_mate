# -*- coding: utf-8 -*-
"""The top of the dock, with more room for the layers.

* Favorites sit in the title bar of the dock, at the right of its title, with the button that folds EXPLORING.
* The source tag (``Vector · OGR``) sits in the layer card, at its top right.
* The row that held both is gone.
* EXPLORING folds away on demand, and by itself while AGENT is the open section; it comes back when another one
  opens, unless the user folded it.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from qgis.PyQt.QtCore import QCoreApplication, QEvent, QObject, QSize, Qt
from qgis.PyQt.QtWidgets import QDockWidget, QHBoxLayout, QLabel, QStyle, QToolButton, QWidget

logger = logging.getLogger("FilterMate")

AGENT_PAGE = "AGENT"
TITLE_BUTTON = 20
TAG_GAP = 8


def _tr(text: str) -> str:
    return QCoreApplication.translate("DockChrome", text)


class DockTitleBar(QWidget):
    """Title, fold EXPLORING, favorites, float and close: a drag or a double click acts as on any dock."""

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
        self.fold_button = self._button("toolButton_fold_exploring")
        self.float_button = self._button("toolButton_dock_float", QStyle.StandardPixmap.SP_TitleBarNormalButton,
                                         _tr("Detach or dock the panel"))
        self.float_button.clicked.connect(lambda: dock.setFloating(not dock.isFloating()))
        self.close_button = self._button("toolButton_dock_close", QStyle.StandardPixmap.SP_TitleBarCloseButton,
                                         _tr("Close"))
        self.close_button.clicked.connect(dock.close)
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(6, 2, 2, 2)
        self._row.setSpacing(4)
        self._row.addWidget(self.title)
        self._row.addStretch(1)
        self._slot = self._row.count()  # favorites go here
        self._row.addWidget(self.fold_button)
        self._row.addWidget(self.float_button)
        self._row.addWidget(self.close_button)
        dock.featuresChanged.connect(self._follow_features)
        self._follow_features(dock.features())

    def _button(self, name: str, pixmap: Any = None, tooltip: str = "") -> QToolButton:
        button = QToolButton(self)
        button.setObjectName(name)
        button.setAutoRaise(True)
        button.setFixedSize(TITLE_BUTTON, TITLE_BUTTON)
        button.setIconSize(QSize(14, 14))
        if pixmap is not None:
            button.setIcon(self.style().standardIcon(pixmap))
        button.setToolTip(tooltip)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    def hold(self, widget: QWidget) -> None:
        """``widget`` at the right of the title, before the buttons of the dock."""
        widget.setParent(self)
        self._row.insertWidget(self._slot, widget)
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


class ExploringFolder(QObject):
    """Folds EXPLORING away and back; folds it by itself while AGENT is open."""

    def __init__(self, dock: Any, button: QToolButton) -> None:
        super().__init__(dock)
        self._frame = dock.frame_exploring
        self._toolbox = dock.toolBox_tabTools
        self._button = button
        self._by_itself = False
        button.clicked.connect(self.toggle)
        self._toolbox.currentChanged.connect(self._on_section)
        self._show_state()

    @property
    def folded(self) -> bool:
        return self._frame.isHidden()

    def set_folded(self, folded: bool) -> None:
        self._frame.setVisible(not folded)
        self._show_state()

    def toggle(self) -> None:
        """The user decides: AGENT will not bring it back."""
        self._by_itself = False
        self.set_folded(not self.folded)

    def follow_section(self) -> None:
        self._on_section(self._toolbox.currentIndex())

    def _on_section(self, index: int) -> None:
        page = self._toolbox.widget(index) if index >= 0 else None
        agent = page is not None and page.objectName() == AGENT_PAGE
        if agent and not self.folded:
            self._by_itself = True
            self.set_folded(True)
        elif not agent and self._by_itself:
            self._by_itself = False
            self.set_folded(False)

    def _show_state(self) -> None:
        folded = self.folded
        pixmap = QStyle.StandardPixmap.SP_TitleBarUnshadeButton if folded else QStyle.StandardPixmap.SP_TitleBarShadeButton
        self._button.setIcon(self._button.style().standardIcon(pixmap))
        self._button.setToolTip(_tr("Show EXPLORING") if folded else _tr("Hide EXPLORING to give room to the sections"))


def install_dock_chrome(dock: Any) -> Optional[DockTitleBar]:
    """Title bar with favorites and the EXPLORING fold; the header row goes. None when it could not be set up."""
    try:
        bar = DockTitleBar(dock)
        dock.setTitleBarWidget(bar)
        favorites = getattr(dock, "favorites_indicator_label", None)
        if favorites is not None:
            favorites.setFixedHeight(TITLE_BUTTON)
            bar.hold(favorites)
        header = getattr(dock, "frame_header", None)
        if header is not None:
            header.setVisible(False)
        if getattr(dock, "frame_exploring", None) is not None and getattr(dock, "toolBox_tabTools", None) is not None:
            dock._fm_exploring_folder = ExploringFolder(dock, bar.fold_button)
        else:
            bar.fold_button.setVisible(False)
        dock._fm_title_bar = bar
        return bar
    except Exception:  # the dock keeps its usual title bar
        logger.exception("Dock title bar could not be set up")
        return None


def put_source_tag_in_card(dock: Any, card: QLabel) -> None:
    """The source tag of ``dock`` at the top right of ``card``."""
    tag = getattr(dock, "backend_indicator_label", None)
    if tag is None or getattr(dock, "_fm_source_tag", None) is not None:
        return
    try:
        dock._fm_source_tag = SourceTag(card, tag)
    except Exception:
        logger.exception("Source tag could not be put in the layer card")
