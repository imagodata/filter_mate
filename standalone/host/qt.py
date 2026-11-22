# -*- coding: utf-8 -*-
"""The few Qt names that moved between Qt5 and Qt6, and the host's translation helper."""

from qgis.PyQt.QtCore import QCoreApplication

try:
    from qgis.PyQt.QtGui import QAction, QActionGroup
except ImportError:  # Qt5
    from qgis.PyQt.QtWidgets import QAction, QActionGroup

try:
    from qgis.PyQt.QtGui import QShortcut
except ImportError:  # Qt5
    from qgis.PyQt.QtWidgets import QShortcut

__all__ = ["QAction", "QActionGroup", "QShortcut", "_tr", "CONTEXT"]

CONTEXT = "FilterMateStandalone"


def _tr(text: str) -> str:
    """A string of the host window, in the language of the application when a catalog has it."""
    return QCoreApplication.translate("FilterMateStandalone", text)
