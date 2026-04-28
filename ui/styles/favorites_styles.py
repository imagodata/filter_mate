# -*- coding: utf-8 -*-
"""Shared QSS / palette / icon registry for the favorites UI.

Centralises the QSS snippets and icon names that
``ui/controllers/favorites_controller.py`` writes onto the indicator
label and the context menu. Keep visual changes here so all favorites
entry points stay in sync.
"""

from __future__ import annotations

from typing import Dict


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
        border: 1px solid #cccccc;
        padding: 5px;
    }
    QMenu::item {
        padding: 6px 20px;
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
    style_data = FAVORITES_STYLES.get(state, FAVORITES_STYLES["empty"])
    return (
        "QLabel#label_favorites_indicator {\n"
        f"    color: {style_data['color']};\n"
        "    font-size: 8pt;\n"
        "    font-weight: 500;\n"
        "    padding: 2px 8px;\n"
        "    border-radius: 10px;\n"
        "    border: none;\n"
        f"    background-color: {style_data['background']};\n"
        "}\n"
        "QLabel#label_favorites_indicator:hover {\n"
        f"    background-color: {style_data['hover']};\n"
        "}\n"
    )


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
