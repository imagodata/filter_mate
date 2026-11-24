# -*- coding: utf-8 -*-
"""Shared QSS / palette / icon registry for the favorites UI.

Centralises the QSS snippets and icon names that
``ui/controllers/favorites_controller.py`` writes onto the indicator
label and the context menu. Keep visual changes here so all favorites
entry points stay in sync.
"""

from __future__ import annotations

import os
from typing import Dict

from .mockup_design import apply_tokens


FAVORITES_STYLES: Dict[str, Dict[str, str]] = {
    "active": {
        "background": "#f39c12",  # Gold/amber
        "hover": "#d68910",
        "color": "white",
    },
    "empty": {
        "background": "#ecf0f1",  # Light gray
        "hover": "#d5dbdb",
        "color": "#95a5a6",
    },
}
"""Indicator badge palette keyed by state (``active`` vs. ``empty``)."""


FAVORITES_MENU_STYLESHEET: str = """
    QMenu {
        background-color: white;
        color: #2c3e50;
        border: 1px solid #cccccc;
        padding: 5px;
    }
    QMenu::item {
        color: #2c3e50;
        padding: 6px 20px;
    }
    QMenu::item:disabled {
        color: #95a5a6;
    }
    QMenu::item:selected {
        background-color: #f39c12;
        color: white;
    }
    QMenu::separator {
        height: 1px;
        background-color: #cccccc;
        margin: 3px 10px;
    }
"""
"""Context menu QSS shared by the dock indicator and the controller menu."""


def build_indicator_stylesheet(state: str) -> str:
    """Return the QSS for the favorites indicator label in a given state.

    States are looked up in ``FAVORITES_STYLES``; unknown states fall
    back to ``empty`` (matches the pre-extraction behaviour).
    """
    # FilterMate 5 design: the square star badge of the mockup (amber once favorites exist).
    from .mockup_design import favorites_badge_stylesheet
    return favorites_badge_stylesheet('label_favorites_indicator', 1 if state == 'active' else 0, dark=False) + "\n"


# Emoji icons used across the favorites menu, indicator and dialog. Kept
# as plain strings (not QIcons) because they ship with every Qt build and
# render uniformly across themes — replace here if a future iteration
# wires SVG resources through ``IconManager``.
ICONS: Dict[str, str] = {
    "favorite": "★",
    "favorite_outline": "☆",
    "add": "⭐",
    "manage": "⚙️",
    "export": "📤",
    "import": "📥",
    "share": "📡",
    "publish": "🚀",
    "remote": "🌐",
    "shared": "👥",
    "owner": "👤",
    "private": "🔒",
    "bullet": "•",
    "quick_filter": "⚡",
    "list": "📋",
}


# Chevron of the dock's combo boxes and spin boxes (resources/styles/spin_down.svg).
_SPIN_DOWN_ICON: str = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "resources", "styles", "spin_down.svg",
).replace("\\", "/")

_DIALOG_STYLESHEET_TEMPLATE: str = """
    QDialog { background-color: {fm_bg}; }
    QLabel { color: {fm_text}; }
    QLabel#dialogHeader {
        font-size: 14pt;
        font-weight: 600;
        padding: 8px 0px;
        margin-bottom: 4px;
    }
    QLabel#infoLabel { color: {fm_text_muted}; font-size: 9pt; }
    QLabel#summaryKey { color: {fm_text_muted}; font-size: 9pt; padding-top: 1px; }
    QLabel#summaryValue { color: {fm_text}; font-size: 10pt; }
    QLabel#scopeBadge {
        color: {fm_text};
        background-color: {fm_active};
        border: 1px solid {fm_active_border};
        border-radius: 9px;
        padding: 2px 10px;
        font-size: 9pt;
        font-weight: 600;
    }
    QScrollArea, QWidget#summaryContent { background: transparent; }
    QLabel#noRemoteLabel {
        color: {fm_text_muted};
        font-style: italic;
        padding: 20px;
    }

    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
        color: {fm_text};
        background-color: {fm_field};
        border: 1px solid {fm_field_border};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 10pt;
        selection-background-color: {fm_active};
        selection-color: {fm_text};
    }
    QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover {
        border-color: {fm_field_hover};
    }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
        border-color: {fm_accent};
    }
    QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled {
        color: {fm_text_disabled};
    }
    QComboBox { padding-right: 24px; }
    /* The native drop-down arrow was cut on the light theme: the same chevron as the dock's. */
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: center right;
        width: 22px;
        border: none;
        background: transparent;
    }
    QComboBox::down-arrow {
        image: url("{spin_down_icon}");
        width: 10px;
        height: 10px;
    }
    QLineEdit#searchEdit { padding: 8px 12px; border-radius: 8px; }
    QComboBox QAbstractItemView {
        color: {fm_text};
        background-color: {fm_list};
        border: 1px solid {fm_field_border};
        selection-background-color: {fm_active};
        selection-color: {fm_text};
    }

    QListWidget, QTableWidget {
        color: {fm_text};
        background-color: {fm_list};
        alternate-background-color: {fm_group};
        border: 1px solid {fm_group_border};
        border-radius: 8px;
        padding: 4px;
        font-size: 10pt;
    }
    QListWidget::item {
        padding: 8px 10px;
        border-radius: 6px;
        margin: 2px 0px;
    }
    QTableWidget::item { padding: 4px; }
    QListWidget::item:selected, QTableWidget::item:selected {
        background-color: {fm_active};
        color: {fm_text};
        border: 1px solid {fm_active_border};
    }
    QListWidget::item:hover:!selected, QTableWidget::item:hover:!selected {
        background-color: {fm_hover};
    }
    QHeaderView::section {
        color: {fm_text_muted};
        background-color: {fm_header};
        padding: 6px 8px;
        border: none;
        border-bottom: 1px solid {fm_group_border};
        font-weight: 500;
        font-size: 9pt;
        text-align: left;
    }

    QTabWidget::pane {
        border: 1px solid {fm_group_border};
        border-radius: 8px;
        background-color: {fm_group};
        padding: 8px;
        margin-top: -1px;
    }
    QTabBar { qproperty-drawBase: 0; }
    QTabBar::tab {
        color: {fm_text_muted};
        background-color: {fm_rail};
        border: 1px solid {fm_group_border};
        border-bottom: none;
        padding: 8px 14px;
        margin-right: 3px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-size: 10pt;
        min-width: 70px;
    }
    QTabBar::tab:selected {
        color: {fm_text};
        background-color: {fm_group};
        border-bottom: 2px solid {fm_accent};
        font-weight: 600;
    }
    QTabBar::tab:hover:!selected {
        color: {fm_text};
        background-color: {fm_hover};
    }

    QPushButton {
        color: {fm_text};
        background-color: {fm_field};
        border: 1px solid {fm_field_border};
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 10pt;
        font-weight: 500;
    }
    QPushButton:hover { background-color: {fm_hover}; border-color: {fm_field_hover}; }
    QPushButton:disabled {
        color: {fm_text_disabled};
        background-color: {fm_group};
        border-color: {fm_group_border};
    }
    QPushButton#applyBtn {
        color: {fm_accent_text};
        background-color: {fm_accent};
        border-color: {fm_accent};
    }
    QPushButton#applyBtn:hover { border-color: {fm_text}; }
    QPushButton#applyBtn:disabled {
        color: {fm_text_disabled};
        background-color: {fm_group};
        border-color: {fm_group_border};
    }
    QPushButton#deleteBtn { color: {fm_danger}; border-color: {fm_danger}; }
    QPushButton#deleteBtn:hover { background-color: {fm_hover}; }
    QPushButton#deleteBtn:disabled {
        color: {fm_text_disabled};
        border-color: {fm_group_border};
    }

    QSplitter::handle { background-color: {fm_group_border}; width: 1px; }
    QSplitter::handle:hover { background-color: {fm_accent}; }
    QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
    QScrollBar::handle:vertical { background: {fm_scroll}; border-radius: 4px; min-height: 24px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
"""Favorites manager dialog QSS; ``{fm_*}`` are the mockup design tokens."""


def favorites_dialog_stylesheet(dark: bool) -> str:
    """QSS of the favorites manager dialog in the dark or the light theme.

    Every color is a ``mockup_design.TOKENS`` value of the chosen variant, so the
    dialog follows the same palette as the dock.
    """
    sheet = apply_tokens(_DIALOG_STYLESHEET_TEMPLATE, dark)
    return sheet.replace("{spin_down_icon}", _SPIN_DOWN_ICON)
