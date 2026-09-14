# -*- coding: utf-8 -*-
"""
Qt6 / QGIS 4 guard (2026-09-14). The plugin repository check of
plugins.qgis.org flags unscoped enum members (``QgsFeatureRequest.NoGeometry``
instead of ``QgsFeatureRequest.Flag.NoGeometry``); PyQt6 removed the unscoped
spellings altogether. This test fails on the spellings that check reports,
so the CI catches them before an upload does.
"""
import ast
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {
    "tests", ".git", "__pycache__",
    "_bmad", "_bmad-output", "website", "docs", "knowledge", "dist", "build", "scripts",
}

# owner name -> members that must be reached through their scoped enum
UNSCOPED_MEMBERS = {
    "Qt": {
        "QueuedConnection", "DirectConnection", "AutoConnection", "BlockingQueuedConnection",
        "UserRole", "DisplayRole", "EditRole", "ToolTipRole", "DecorationRole", "CheckStateRole",
        "Checked", "Unchecked", "PartiallyChecked",
        "WaitCursor", "BusyCursor", "ArrowCursor", "PointingHandCursor",
        "AlignLeft", "AlignRight", "AlignHCenter", "AlignTop", "AlignBottom", "AlignVCenter", "AlignCenter",
        "LeftButton", "RightButton", "MiddleButton", "Horizontal", "Vertical",
        "StrongFocus", "NoFocus", "ClickFocus", "TabFocus", "CustomContextMenu", "NoContextMenu",
        "KeepAspectRatio", "IgnoreAspectRatio", "SmoothTransformation", "FastTransformation",
        "ElideRight", "ElideLeft", "ElideNone", "RichText", "PlainText",
        "ItemIsEnabled", "ItemIsSelectable", "ItemIsUserCheckable", "ItemIsEditable",
        "MatchExactly", "MatchContains", "MatchFixedString", "MatchStartsWith",
        "WA_DeleteOnClose", "WA_TransparentForMouseEvents", "WA_StyledBackground",
        "ScrollBarAlwaysOff", "ScrollBarAlwaysOn", "ScrollBarAsNeeded",
        "black", "white", "red", "blue", "green", "gray", "transparent", "darkGray", "lightGray",
        "Window", "Dialog", "Tool", "Popup", "FramelessWindowHint", "WindowStaysOnTopHint",
        "Key_Escape", "Key_Return", "Key_Enter", "Key_Delete", "Key_Backspace", "Key_Tab", "Key_Space",
    },
    "QgsFeatureRequest": {"NoGeometry", "ExactIntersect", "NoFlags", "SubsetOfAttributes", "EmbeddedSymbols"},
    "QgsWkbTypes": {
        "Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon",
        "NoGeometry", "Unknown", "GeometryCollection",
        "PointGeometry", "LineGeometry", "PolygonGeometry", "NullGeometry", "UnknownGeometry",
    },
    "QMessageBox": {"Yes", "No", "Ok", "Cancel", "Warning", "Critical", "Information", "Question", "Save", "Discard"},
    "QDialog": {"Accepted", "Rejected"},
    "QSizePolicy": {"Expanding", "Fixed", "Minimum", "Maximum", "Preferred", "MinimumExpanding", "Ignored"},
    "QHeaderView": {"Stretch", "ResizeToContents", "Interactive", "Fixed"},
    "QAbstractItemView": {"SingleSelection", "ExtendedSelection", "MultiSelection", "NoSelection",
                          "SelectRows", "SelectItems", "NoEditTriggers", "DoubleClicked"},
    "QFrame": {"StyledPanel", "NoFrame", "Box", "Panel", "HLine", "VLine", "Sunken", "Raised", "Plain"},
    "QLineEdit": {"Normal", "Password", "NoEcho"},
    "QFont": {"Bold", "Normal", "Light", "DemiBold"},
    "QImage": {"Format_ARGB32", "Format_RGB32", "Format_RGBA8888"},
    "QPainter": {"Antialiasing", "SmoothPixmapTransform"},
    "QTabWidget": {"North", "South", "Rounded", "Triangular"},
    "QComboBox": {"NoInsert", "InsertAtBottom", "AdjustToContents"},
    "QLayout": {"SetFixedSize", "SetMinimumSize", "SetDefaultConstraint"},
}
REMOVED_METHODS = {"exec_"}


def _plugin_python_files():
    for path in PLUGIN_ROOT.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(PLUGIN_ROOT).parts):
            continue
        yield path


def _offences(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            owner = node.value
            owner_name = owner.id if isinstance(owner, ast.Name) else (
                owner.attr if isinstance(owner, ast.Attribute) else None)
            if owner_name in UNSCOPED_MEMBERS and node.attr in UNSCOPED_MEMBERS[owner_name]:
                yield node.lineno, f"{owner_name}.{node.attr}"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in REMOVED_METHODS:
            yield node.lineno, f".{node.func.attr}()"


@pytest.mark.unit
def test_no_unscoped_qt_or_qgis_enum_members():
    offenders = []
    for path in _plugin_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for lineno, what in _offences(tree):
            offenders.append(f"{path.relative_to(PLUGIN_ROOT)}:{lineno} {what}")
    assert offenders == [], (
        "Unscoped enum members are rejected by the QGIS plugin repository Qt6 check; "
        "use the scoped form (Qt.ConnectionType.QueuedConnection, QgsWkbTypes.Type.Point, "
        "QMessageBox.StandardButton.Yes, ...):\n" + "\n".join(offenders)
    )
